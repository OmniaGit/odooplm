# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""A tool defined from the screen, as a server action.

The tools in the other files of this folder are methods, written once and
shipped with the module. This is the other way to have one: an administrator
opens a server action of type *Execute Code*, ticks *Use as PLM MCP Tool*, names
it, describes it and says what arguments it takes, and the tool is there for the
next question — no module to write, no restart.

Three things decide how it behaves, each read from core rather than assumed:

- the code returns what it assigns to ``action``: that is what core's runner
  hands back for a code action, so a tool sets ``action = {...}``;
- it runs in the *user's* environment, not in sudo — core evaluates server-action
  code with the caller's ``env`` and reads only the action record itself with
  sudo — so the record rules that bound the person bound the tool;
- core's own access check is not used. With no groups on the action it demands
  *write* access on the model, which would hide every read tool from a user who
  can only read. The rule here asks for read where the tool is read-only.

Only system administrators can create or change a server action (core's access
rights), so who writes the tools is the same short list who can already run
code on the server.
"""
import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

TOOL_NAME = re.compile(r"^[a-zA-Z0-9_]{1,64}$")

# The JSON Schema types that are checked on the way in. Anything else, or a
# property that declares none, is passed through as the client sent it.
JSON_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    # Prefixed, so these cannot meet the fields Odoo's own ai and ai_mcp add to
    # this model when they are installed alongside.
    plm_mcp_enabled = fields.Boolean(
        string="Use as PLM MCP Tool", copy=False,
        help="Offer this action as a tool of the PLM MCP server.",
    )
    plm_mcp_tool_name = fields.Char(
        string="MCP Tool Name", copy=False,
        help="What the client calls it: letters, digits and underscores, "
             "up to 64.",
    )
    plm_mcp_description = fields.Text(
        string="MCP Tool Description", copy=False,
        help="Written for the AI, not for a developer: say what comes back and "
             "when this tool is the right one. It is all the AI has to decide.",
    )
    plm_mcp_schema = fields.Text(
        string="MCP Arguments Schema", copy=False,
        help="JSON Schema of the arguments, e.g. "
             '{"type": "object", "properties": {"code": {"type": "string"}}, '
             '"required": ["code"]}. Leave empty for a tool without arguments.',
    )
    plm_mcp_readonly = fields.Boolean(
        string="MCP Read-only Tool", copy=False,
        help="Tick it when the tool only reads. The client is told, and the "
             "person only needs read access on the model, not write.",
    )

    _plm_mcp_tool_name_uniq = models.UniqueIndex(
        "(plm_mcp_tool_name) WHERE plm_mcp_enabled IS TRUE",
        "Another MCP tool already has that name.",
    )

    # ------------------------------------------------------------ validation
    @api.constrains("plm_mcp_enabled", "plm_mcp_tool_name",
                    "plm_mcp_description", "plm_mcp_schema", "state")
    def _check_plm_mcp_tool(self):
        built_in = self.env["plm.mcp.tool"]._tool_specs()
        for action in self.filtered("plm_mcp_enabled"):
            if action.state != "code":
                raise ValidationError(_(
                    "Only an Execute Code action can be an MCP tool: %s.",
                    action.name))
            name = action.plm_mcp_tool_name
            if not name or not TOOL_NAME.match(name):
                raise ValidationError(_(
                    "The MCP tool name must be 1 to 64 letters, digits or "
                    "underscores."))
            if name in built_in:
                raise ValidationError(_(
                    "%s is the name of a built-in PLM tool.", name))
            if not (action.plm_mcp_description or "").strip():
                raise ValidationError(_("An MCP tool needs a description."))
            action._plm_mcp_parse_schema()

    def _plm_mcp_parse_schema(self):
        """The arguments schema as a dict MCP can use, or raise.

        ``type``, ``properties`` and ``required`` are always present in what is
        returned: a client expects an object schema even for a tool that takes
        nothing.
        """
        self.ensure_one()
        text = (self.sudo().plm_mcp_schema or "").strip()
        try:
            schema = json.loads(text) if text else {}
        except ValueError:
            raise ValidationError(_("The arguments schema is not valid JSON."))

        properties = schema.get("properties", {}) if isinstance(schema, dict) else None
        required = schema.get("required", []) if isinstance(schema, dict) else None
        if not isinstance(properties, dict) or not isinstance(required, list) \
                or schema.get("type", "object") != "object" \
                or not all(isinstance(p, dict) for p in properties.values()):
            raise ValidationError(_(
                "The arguments schema must be a JSON Schema object with "
                "properties and required."))
        for name in required:
            if name not in properties:
                raise ValidationError(_(
                    "The argument %s is required but not declared.", name))
        schema.update(type="object", properties=properties, required=required)
        return schema

    # ----------------------------------------------------------------- access
    def _plm_mcp_can_run(self):
        """Whether the current user may run this action as a tool. Never raises.

        Groups on the action decide when there are any. Otherwise the person
        needs read access on the model for a read-only tool and write access for
        any other — the one place this differs from core, for the reason given
        at the top.
        """
        self.ensure_one()
        action = self.sudo()
        if action.group_ids:
            return bool(action.group_ids & self.env.user.all_group_ids)
        mode = "read" if action.plm_mcp_readonly else "write"
        model = self.env.get(action.model_id.model)
        return model is not None and model.has_access(mode)

    @api.model
    def _plm_mcp_tools(self):
        """The enabled tools the current user may run, as ``{name: action}``."""
        tools = {}
        for action in self.sudo().search([("plm_mcp_enabled", "=", True)]):
            action = action.with_env(self.env)
            if action._plm_mcp_can_run():
                tools[action.sudo().plm_mcp_tool_name] = action
        return tools

    # -------------------------------------------------------------------- run
    def _plm_mcp_run(self, arguments):
        """Run the code with ``arguments`` and return what it set as ``action``.

        The evaluation context is built from the user's environment, so ``env``
        in the code is the person's; the action itself is read in sudo, which is
        how core's own ``run`` treats it.
        """
        self.ensure_one()
        action = self.sudo()
        eval_context = self._get_eval_context(action)
        eval_context["arguments"] = arguments
        return action._run(eval_context["model"], eval_context)
