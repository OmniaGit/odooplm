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
"""The MCP endpoint: one route, JSON-RPC in, JSON-RPC out.

The transport is Streamable HTTP, which for a server that keeps no session is
just a POST carrying one JSON-RPC message. That is why this fits in an ordinary
Odoo controller with no separate process: nothing here needs an event loop.

The message shapes come from ``mcp_types`` — the wire types published by the
protocol's authors — rather than being assembled by hand. The current revision
adds fields to results that hand-written dictionaries quietly get wrong, and
letting the package own them means a protocol update is a dependency bump
instead of a reading exercise.

The route is ``auth="none"`` because the caller is an MCP client holding a
bearer token, not a session; the token is resolved to a plm.mcp.key, and every
tool then runs in that key's user environment.
"""
import json
import logging

from mcp_types import (
    DEFAULT_NEGOTIATED_VERSION,
    LATEST_PROTOCOL_VERSION,
    Implementation,
    InitializeResult,
    ServerCapabilities,
)
from odoo.http import Controller, Response, request, route

from ..models.plm_mcp_tool import McpInvalidArguments, McpToolNotFound

_logger = logging.getLogger(__name__)

ENDPOINT = "/plm/mcp"

# The revisions this server answers on. The package supplies the constants; the
# policy of which ones to accept is ours, and staying deliberately narrow means
# there is no per-revision behaviour to maintain — a client asking for anything
# else is told plainly which one it gets.
SUPPORTED_VERSIONS = (LATEST_PROTOCOL_VERSION, DEFAULT_NEGOTIATED_VERSION)

# JSON-RPC 2.0 error codes, plus the one MCP adds for an unknown tool.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _json(payload, status=200):
    return Response(
        json.dumps(payload, default=str),
        status=status,
        content_type="application/json",
    )


def _error(request_id, code, message):
    return _json({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    })


def _result(request_id, result):
    return _json({"jsonrpc": "2.0", "id": request_id, "result": result})


class PlmMcpController(Controller):

    # readonly=False is not decoration. Since 18.0 a route declared auth="none"
    # is served with a read-only cursor unless it says otherwise, and this one
    # writes on every call — _register_call stamps the key. Left implicit, each
    # request would run, fail on that write and be replayed from the top by the
    # framework with a read/write cursor: correct answers, twice the work.
    @route(ENDPOINT, type="http", auth="none", methods=["POST"], csrf=False,
           save_session=False, readonly=False)
    def mcp(self, **kwargs):
        key = self._authenticate()
        if not key:
            # 401 rather than a JSON-RPC error: the request never reached the
            # protocol, and an MCP client is expected to read the HTTP status.
            return _json({"error": "unauthorized"}, status=401)

        try:
            body = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError:
            return _error(None, PARSE_ERROR, "Body is not valid JSON.")

        if isinstance(body, list):
            # Batches are not part of the current revision and nothing sends
            # them; refusing plainly beats answering half of one.
            return _error(None, INVALID_REQUEST, "Batch requests are not supported.")
        if not isinstance(body, dict) or "method" not in body:
            return _error(None, INVALID_REQUEST, "Not a JSON-RPC request.")

        method = body.get("method")
        request_id = body.get("id")
        params = body.get("params") or {}

        # No id means a notification: the client wants no answer, and the
        # protocol says not to send one.
        if request_id is None and not method.startswith("notifications/"):
            _logger.debug("plm_mcp: request without id for %s", method)
        if method.startswith("notifications/"):
            return Response(status=202)

        key._register_call()
        try:
            return self._dispatch(key, method, params, request_id)
        except Exception:
            # The traceback belongs in the log, not in a payload an agent will
            # read back to a user.
            _logger.exception("plm_mcp: %s failed for key %s", method, key.name)
            return _error(request_id, INTERNAL_ERROR, "Internal error.")

    # ------------------------------------------------------------- dispatch
    def _dispatch(self, key, method, params, request_id):
        if method == "initialize":
            return _result(request_id, self._initialize(params))
        if method == "ping":
            return _result(request_id, {})
        if method == "tools/list":
            # Listed through the key's user: a tool the user cannot reach is a
            # tool the agent should not be told about in the first place.
            tools = key.user_env()["plm.mcp.tool"]._list_tools()
            return _result(request_id, tools)
        if method == "tools/call":
            return self._call(key, params, request_id)
        return _error(request_id, METHOD_NOT_FOUND, "Unknown method %r." % method)

    def _call(self, key, params, request_id):
        """Run one tool as the key's user.

        Only a malformed call answers with a JSON-RPC error. A tool that ran and
        could not answer comes back as a normal result carrying isError, because
        that is a fact about the data the model should reason about — "there is
        no part with that code" is an answer, not a transport failure.
        """
        name = (params or {}).get("name")
        arguments = (params or {}).get("arguments") or {}
        if not name:
            return _error(request_id, INVALID_PARAMS, "No tool name given.")

        tools = key.user_env()["plm.mcp.tool"]
        try:
            result = tools._call_tool(name, arguments)
        except McpToolNotFound:
            return _error(request_id, INVALID_PARAMS, "Unknown tool %r." % name)
        except McpInvalidArguments as missing:
            return _error(request_id, INVALID_PARAMS,
                          "Missing required argument(s): %s." % missing)
        return _result(request_id, result)

    def _initialize(self, params):
        """Agree on a revision and say what this server can do.

        The client names the revision it wants. If it is one we answer on, that
        is the answer; otherwise we name ours and let the client decide whether
        to continue — which is what the specification asks for, and is more
        useful than an error the user never sees.
        """
        asked = (params or {}).get("protocolVersion")
        version = asked if asked in SUPPORTED_VERSIONS else LATEST_PROTOCOL_VERSION
        if asked and asked != version:
            _logger.info("plm_mcp: client asked for %s, answering on %s",
                         asked, version)

        result = InitializeResult(
            protocolVersion=version,
            capabilities=ServerCapabilities(tools={"listChanged": False}),
            serverInfo=Implementation(name="odooplm", version=self._version()),
        )
        return result.model_dump(by_alias=True, exclude_none=True)

    # ---------------------------------------------------------------- helpers
    def _authenticate(self):
        """The key behind the bearer token, or an empty recordset."""
        header = request.httprequest.headers.get("Authorization") or ""
        token = header[7:].strip() if header[:7].lower() == "bearer " else ""
        return request.env["plm.mcp.key"].sudo()._authenticate(token)

    def _version(self):
        """The installed version of this module, for serverInfo."""
        module = request.env["ir.module.module"].sudo().search(
            [("name", "=", "plm_mcp")], limit=1)
        return module.installed_version or "unknown"
