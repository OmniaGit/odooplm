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

from mcp_types import CallToolResult, TextContent, Tool
from odoo import _, api, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class McpToolNotFound(Exception):
    """The client asked for a tool that is not declared."""


class McpInvalidArguments(Exception):
    """The call is missing an argument the tool declares as required."""


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
        tools = []
        for _method_name, spec in self._tool_specs().values():
            tool = Tool(
                name=spec["name"],
                description=spec["description"],
                inputSchema=spec["inputSchema"],
            )
            tools.append(tool.model_dump(by_alias=True, exclude_none=True))
        return {"tools": tools}

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
            raise McpToolNotFound(name)

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
