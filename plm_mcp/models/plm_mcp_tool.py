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
##############################################################################
"""Where the tools live, and how they are found.

A tool is a method on this abstract model, tagged with the ``mcp_tool``
decorator. The registry finds it by walking the class hierarchy, so another
module that inherits this model and adds its own decorated method has a working
tool — no registration call, no data file to keep in step with the code.

Descriptions are the part worth spending time on. What reaches the model at
tools/list is the name, the description and the parameter schema, and that is
all it has to decide whether the tool answers the question in front of it. A
description that says what the tool returns, and when it is the right one, is
worth more than any amount of implementation.
"""
import json
import logging

from mcp_types import CallToolResult, TextContent, Tool, ToolAnnotations
from odoo import _, api, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .ir_actions_server import JSON_TYPES

_logger = logging.getLogger(__name__)


class McpToolNotFound(Exception):
    """The client asked for a tool that is not declared."""


class McpInvalidArguments(Exception):
    """The call is missing an argument the tool declares as required."""


class McpBadArgument(McpInvalidArguments):
    """An argument is there but is not of the type the tool declares.

    Its text is the whole message, unlike the parent's, which is only the names
    of the missing arguments.
    """


def mcp_tool(name, description, properties=None, required=None):
    """Tag a method as a tool.

    :param name: what the client calls. Prefixed ``plm_`` by convention, so the
        tools of this suite are recognisable among whatever else a client has
        connected.
    :param description: written for the model, not for a developer. Say what
        comes back and when to reach for it.
    :param properties: JSON Schema properties of the arguments.
    :param required: names of the arguments that must be supplied.
    """
    def decorator(func):
        func._mcp_tool = {
            "name": name,
            "description": description.strip(),
            "inputSchema": {
                "type": "object",
                "properties": properties or {},
                "required": list(required or ()),
            },
        }
        return func
    return decorator


class PlmMcpTool(models.AbstractModel):
    _name = "plm.mcp.tool"
    _description = "PLM MCP Tools"

    # ------------------------------------------------------------- registry
    @api.model
    def _tool_specs(self):
        """Every declared tool, as ``{name: (method_name, spec)}``.

        The walk is over the class dictionaries rather than ``dir()`` so that
        nothing is resolved through a descriptor on the way, and it runs from
        the base of the hierarchy upwards: a module that inherits this model and
        redeclares a tool under the same name replaces it rather than colliding
        with it.
        """
        specs = {}
        for klass in reversed(type(self).__mro__):
            for method_name, value in vars(klass).items():
                spec = getattr(value, "_mcp_tool", None)
                if spec:
                    specs[spec["name"]] = (method_name, spec)
        return dict(sorted(specs.items()))

    @api.model
    def _list_tools(self):
        """The tools/list payload, in a stable order.

        Sorted by name because the list travels in the model's context on every
        conversation: a stable order keeps the prompt prefix stable, and an
        unstable one would quietly cost cache hits on every call.
        """
        tools = {}
        for _method_name, spec in self._tool_specs().values():
            tool = Tool(
                name=spec["name"],
                description=spec["description"],
                inputSchema=spec["inputSchema"],
            )
            tools[spec["name"]] = tool.model_dump(by_alias=True, exclude_none=True)

        # The tools an administrator defined from the screen, offered only to
        # the people allowed to run them. A name cannot be both, which the
        # action's own constraint guarantees.
        for name, action in self.env["ir.actions.server"]._plm_mcp_tools().items():
            definition = action.sudo()
            tool = Tool(
                name=name,
                description=definition.plm_mcp_description.strip(),
                inputSchema=definition._plm_mcp_parse_schema(),
                annotations=ToolAnnotations(
                    read_only_hint=definition.plm_mcp_readonly,
                    destructive_hint=not definition.plm_mcp_readonly,
                ),
            )
            tools[name] = tool.model_dump(by_alias=True, exclude_none=True)
        return {"tools": [tools[name] for name in sorted(tools)]}

    # ------------------------------------------------------------- execution
    @api.model
    def _call_tool(self, name, arguments):
        """Run a tool and package what it returns.

        Two kinds of failure, deliberately kept apart. A tool that does not
        exist, or a call missing a required argument, is a fault in the request:
        it raises, and the endpoint answers with a JSON-RPC error. A tool that
        ran and could not answer — no part with that code, nothing to compare —
        is a *result*: it comes back as an error result the model reads and acts
        on, which is what lets an agent say "there is no such part" instead of
        reporting that the server is broken.
        """
        specs = self._tool_specs()
        if name not in specs:
            return self._call_screen_tool(name, arguments)

        method_name, spec = specs[name]
        declared = spec["inputSchema"]["properties"]
        arguments = arguments or {}

        missing = [n for n in spec["inputSchema"]["required"] if n not in arguments]
        if missing:
            raise McpInvalidArguments(", ".join(missing))

        # Only declared arguments are passed on: a client that invents an extra
        # one gets it ignored rather than a TypeError from the method.
        #
        # Nulls are dropped with them. A client that sends "revision": null
        # means "no revision given", not "the null revision", and passing it
        # through would override the method's default — turning an omitted
        # latest_only into False, which is the opposite of what was asked. Odoo's
        # own agent fills every declared argument with None before calling, so
        # without this every optional default would be lost there.
        kwargs = {n: v for n, v in arguments.items() if n in declared and v is not None}
        unknown = set(arguments) - set(declared)
        if unknown:
            _logger.debug("plm_mcp: %s called with undeclared arguments %s",
                          name, sorted(unknown))

        try:
            payload = getattr(self, method_name)(**kwargs)
        except (UserError, ValidationError, AccessError) as error:
            _logger.info("plm_mcp: %s refused: %s", name, error)
            return self._tool_error(str(error))

        return self._tool_result(payload)

    @api.model
    def _call_screen_tool(self, name, arguments):
        """Run a tool an administrator defined from the screen.

        Same two kinds of failure as above. A tool the person may not run is not
        there for them, so it is reported exactly as one that does not exist.
        The code is an administrator's, so what goes wrong inside it is logged
        in full but never put in front of the AI: an error of its own making
        (a user error, an access error) is shown as the result, anything else
        only says that the tool failed.
        """
        action = self.env["ir.actions.server"]._plm_mcp_tools().get(name)
        if not action:
            raise McpToolNotFound(name)

        schema = action._plm_mcp_parse_schema()
        kwargs = self._screen_tool_arguments(schema, arguments or {})
        try:
            payload = action._plm_mcp_run(kwargs)
        except (UserError, ValidationError, AccessError) as error:
            _logger.info("plm_mcp: %s refused: %s", name, error)
            return self._tool_error(str(error))
        except Exception:
            _logger.exception("plm_mcp: the tool %s failed", name)
            return self._tool_error(_("The tool failed. The details are in the server log."))

        if not payload:
            payload = _("The operation has been executed successfully.")
        return self._tool_result(payload)

    @api.model
    def _screen_tool_arguments(self, schema, arguments):
        """The arguments the code is given, checked against its schema.

        Required ones must be there and not null; an argument that is declared
        must be of its declared type; one that is not declared is dropped, as
        for the built-in tools. A boolean is not accepted as a number, though
        Python would count it as one.
        """
        properties = schema["properties"]
        missing = [n for n in schema["required"] if arguments.get(n) is None]
        if missing:
            raise McpInvalidArguments(", ".join(missing))

        kwargs = {n: v for n, v in arguments.items() if n in properties and v is not None}
        for argument, value in kwargs.items():
            declared = properties[argument].get("type")
            expected = JSON_TYPES.get(declared) if isinstance(declared, str) else None
            if expected and (not isinstance(value, expected)
                             or (isinstance(value, bool) and declared != "boolean")):
                raise McpBadArgument(
                    _("The argument %(name)s must be of type %(type)s.",
                      name=argument, type=declared))
        return kwargs

    @api.model
    def _tool_result(self, payload):
        """A successful result, as both structured data and text.

        structuredContent is what a client should read; the text block carries
        the same payload for clients that only handle text. Sending one without
        the other would make the tool work on some clients and not others.
        """
        result = CallToolResult(
            content=[TextContent(
                type="text", text=json.dumps(payload, default=str, ensure_ascii=False),
            )],
            structuredContent=payload if isinstance(payload, dict) else None,
            isError=False,
        )
        return result.model_dump(by_alias=True, exclude_none=True)

    @api.model
    def _tool_error(self, message):
        result = CallToolResult(
            content=[TextContent(type="text", text=message)],
            isError=True,
        )
        return result.model_dump(by_alias=True, exclude_none=True)

    @api.model
    def _no_part(self, code, revision=None):
        """The message a tool returns when a part simply is not there."""
        if revision is None:
            return _("No part with engineering code %s.") % code
        return _("No part %s at revision %s.") % (code, revision)
