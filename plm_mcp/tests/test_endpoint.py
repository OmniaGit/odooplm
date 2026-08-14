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
"""The endpoint, exercised over HTTP the way a client reaches it.

The tests above call the tools in Python; these go through the route, because
the parts that break in production are the ones in between — the bearer header,
the JSON-RPC envelope, the status code an unauthenticated client is supposed to
read.

    odoo --test-tags=odoo_plm_mcp -i plm_mcp -d <database>
"""
import json

from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger

ENDPOINT = "/plm/mcp"


@tagged("-standard", "odoo_plm_mcp")
class TestEndpoint(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create({
            "name": "MCP endpoint user",
            "login": "mcp_endpoint_user",
            # A plain internal user cannot read mrp.bom, and the tools would refuse
            # for that reason alone. The rights given here are the ones a
            # person asking these questions would actually have.
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("mrp.group_mrp_user").id,
            ])],
        })
        cls.key = cls.env["plm.mcp.key"].create({
            "name": "Endpoint test key",
            "user_id": cls.user.id,
        })
        cls.token = cls.key.key_clear

    def post(self, payload, token=None):
        """One JSON-RPC message, with a bearer token unless told otherwise."""
        headers = {"Content-Type": "application/json"}
        if token is not False:
            headers["Authorization"] = "Bearer %s" % (token or self.token)
        return self.url_open(
            ENDPOINT, data=json.dumps(payload), headers=headers)

    # ------------------------------------------------------------------ auth
    @mute_logger("odoo.http")
    def test_no_token_is_refused_with_401(self):
        """The status code matters: a client reads it before the body."""
        response = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"},
                             token=False)
        self.assertEqual(response.status_code, 401)

    @mute_logger("odoo.http")
    def test_a_wrong_token_is_refused_with_401(self):
        response = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"},
                             token="not-a-real-token")
        self.assertEqual(response.status_code, 401)

    # -------------------------------------------------------------- protocol
    def test_ping(self):
        response = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], {})

    def test_initialize_answers_with_a_version_and_the_server_name(self):
        response = self.post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        })
        result = response.json()["result"]
        self.assertTrue(result["protocolVersion"])
        self.assertEqual(result["serverInfo"]["name"], "odooplm")
        self.assertIn("tools", result["capabilities"])

    def test_initialize_keeps_a_version_it_supports(self):
        """Negotiation, not imposition: what the client asked for, if we answer it."""
        supported = self.post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {},
        }).json()["result"]["protocolVersion"]

        response = self.post({
            "jsonrpc": "2.0", "id": 2, "method": "initialize",
            "params": {"protocolVersion": supported},
        })
        self.assertEqual(response.json()["result"]["protocolVersion"], supported)

    def test_tools_are_listed(self):
        response = self.post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [tool["name"] for tool in response.json()["result"]["tools"]]
        self.assertIn("plm_find_part", names)
        self.assertIn("plm_overview", names)

    def test_a_tool_can_be_called(self):
        response = self.post({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "plm_overview", "arguments": {}},
        })
        result = response.json()["result"]
        self.assertFalse(result["isError"])
        self.assertIn("structuredContent", result)

    def test_an_unknown_method_is_a_jsonrpc_error(self):
        response = self.post({
            "jsonrpc": "2.0", "id": 1, "method": "does/not/exist"})
        self.assertEqual(response.json()["error"]["code"], -32601)

    def test_an_unknown_tool_is_an_invalid_params_error(self):
        response = self.post({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "plm_not_a_tool", "arguments": {}},
        })
        self.assertEqual(response.json()["error"]["code"], -32602)

    def test_a_missing_required_argument_is_an_invalid_params_error(self):
        response = self.post({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "plm_part_detail", "arguments": {}},
        })
        self.assertEqual(response.json()["error"]["code"], -32602)

    def test_a_tool_that_cannot_answer_returns_a_result_not_an_error(self):
        """"There is no such part" is data, and the model must see it as data."""
        response = self.post({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "plm_part_detail",
                       "arguments": {"code": "MCPT-NO-SUCH-CODE"}},
        })
        body = response.json()
        self.assertNotIn("error", body)
        self.assertTrue(body["result"]["isError"])

    @mute_logger("odoo.http")
    def test_a_body_that_is_not_json_is_a_parse_error(self):
        response = self.url_open(
            ENDPOINT, data="{not json",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer %s" % self.token})
        self.assertEqual(response.json()["error"]["code"], -32700)

    def test_a_notification_gets_no_answer(self):
        response = self.post({
            "jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(response.status_code, 202)

    # ------------------------------------------------------------- behaviour
    def test_a_call_is_counted_once(self):
        """Once, not twice.

        A route declared auth="none" is served with a read-only cursor unless it
        says otherwise; this one writes, so without readonly=False the request
        fails on that write and the framework replays it whole. The answer would
        still be right, which is why only the count gives it away.
        """
        before = self.key.call_count
        self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        self.key.invalidate_recordset()
        self.assertEqual(self.key.call_count, before + 1)

    def test_calls_run_as_the_keys_user(self):
        self.post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.key.invalidate_recordset()
        self.assertTrue(self.key.last_used_on)
