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
"""Tools defined from the screen, exercised the way the endpoint uses them.

    odoo --test-tags=odoo_plm_mcp -u plm_mcp -d <database>

What is checked is the contract of a tool an administrator writes: it appears
for the people who may run it and for nobody else, it receives its arguments
already checked, it runs as the person asking, and what goes wrong inside it
never reaches the AI except as a plain message.
"""
import json

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase
from odoo.tools import mute_logger

from odoo.addons.plm_mcp.models.plm_mcp_tool import (
    McpBadArgument,
    McpInvalidArguments,
    McpToolNotFound,
)

SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "count": {"type": "integer"},
        "flag": {"type": "boolean"},
    },
    "required": ["text"],
})


class ScreenToolCase:
    """The helpers both kinds of test below use."""

    def make_tool(self, name="plm_test_tool", code="action = {}", **extra):
        values = {
            "name": "Test tool %s" % name,
            "model_id": self.env.ref("product.model_product_product").id,
            "state": "code",
            "code": code,
            "plm_mcp_enabled": True,
            "plm_mcp_tool_name": name,
            "plm_mcp_description": "A tool made for a test.",
            "plm_mcp_readonly": True,
        }
        values.update(extra)
        return self.env["ir.actions.server"].create(values)

    def make_user(self, login):
        return self.env["res.users"].create({
            "name": login,
            "login": login,
            "password": "%s_pw_2026" % login,
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })

    def names(self, env):
        return [tool["name"] for tool in env["plm.mcp.tool"]._list_tools()["tools"]]


@tagged("-standard", "odoo_plm_mcp")
class TestScreenTools(ScreenToolCase, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.make_user(cls, "screen_tool_user")
        cls.user_env = cls.env(user=cls.user.id)
        cls.admin_env = cls.env(user=cls.env.ref("base.user_admin").id)

    # --------------------------------------------------------------- listing
    def test_an_enabled_tool_is_listed_with_its_schema_and_hints(self):
        self.make_tool(plm_mcp_schema=SCHEMA)
        listed = {t["name"]: t for t in self.user_env["plm.mcp.tool"]._list_tools()["tools"]}
        tool = listed["plm_test_tool"]
        self.assertEqual(tool["description"], "A tool made for a test.")
        self.assertEqual(tool["inputSchema"]["required"], ["text"])
        self.assertTrue(tool["annotations"]["readOnlyHint"])
        self.assertFalse(tool["annotations"]["destructiveHint"])

    def test_a_tool_that_is_not_read_only_says_so(self):
        self.make_tool(plm_mcp_readonly=False)
        tool = next(t for t in self.admin_env["plm.mcp.tool"]._list_tools()["tools"]
                    if t["name"] == "plm_test_tool")
        self.assertFalse(tool["annotations"]["readOnlyHint"])
        self.assertTrue(tool["annotations"]["destructiveHint"])

    def test_a_disabled_tool_is_not_listed(self):
        self.make_tool(plm_mcp_enabled=False)
        self.assertNotIn("plm_test_tool", self.names(self.user_env))

    def test_the_built_in_tools_are_still_there_and_the_order_is_stable(self):
        self.make_tool("plm_aaa_first")
        names = self.names(self.user_env)
        self.assertIn("plm_overview", names)
        self.assertIn("plm_aaa_first", names)
        self.assertEqual(names, sorted(names))

    # ---------------------------------------------------------------- access
    def test_allowed_groups_decide_who_sees_and_who_may_call(self):
        self.make_tool(group_ids=[(6, 0, [self.env.ref("base.group_system").id])])
        self.assertNotIn("plm_test_tool", self.names(self.user_env))
        with self.assertRaises(McpToolNotFound):
            self.user_env["plm.mcp.tool"]._call_tool("plm_test_tool", {})
        self.assertIn("plm_test_tool", self.names(self.admin_env))

    def test_a_read_only_tool_needs_only_read_access(self):
        country = self.user_env["res.country"]
        self.assertTrue(country.has_access("read"))
        self.assertFalse(country.has_access("write"), "the premise of this test")
        model = self.env.ref("base.model_res_country")
        self.make_tool("plm_reader", model_id=model.id, plm_mcp_readonly=True)
        self.make_tool("plm_writer", model_id=model.id, plm_mcp_readonly=False)
        names = self.names(self.user_env)
        self.assertIn("plm_reader", names)
        self.assertNotIn("plm_writer", names)

    # ------------------------------------------------------------- execution
    def test_the_code_runs_as_the_person_asking(self):
        self.make_tool(code="action = {'login': env.user.login, 'su': env.su}")
        result = self.user_env["plm.mcp.tool"]._call_tool("plm_test_tool", {})
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"],
                         {"login": "screen_tool_user", "su": False})

    def test_the_code_receives_the_arguments_checked(self):
        self.make_tool(plm_mcp_schema=SCHEMA,
                       code="action = {'text': arguments['text'], "
                            "'count': arguments.get('count'), "
                            "'seen': sorted(arguments)}")
        result = self.user_env["plm.mcp.tool"]._call_tool(
            "plm_test_tool",
            {"text": "hi", "count": None, "unknown": 1})
        # the null is dropped, the undeclared one is dropped
        self.assertEqual(result["structuredContent"],
                         {"text": "hi", "count": None, "seen": ["text"]})

    def test_a_missing_required_argument_is_a_fault_of_the_request(self):
        self.make_tool(plm_mcp_schema=SCHEMA)
        with self.assertRaises(McpInvalidArguments):
            self.user_env["plm.mcp.tool"]._call_tool("plm_test_tool", {})
        with self.assertRaises(McpInvalidArguments):
            self.user_env["plm.mcp.tool"]._call_tool("plm_test_tool", {"text": None})

    def test_an_argument_of_the_wrong_type_is_refused(self):
        self.make_tool(plm_mcp_schema=SCHEMA)
        for arguments in ({"text": 5}, {"text": "a", "count": "3"},
                          {"text": "a", "count": True}, {"text": "a", "flag": 1}):
            with self.subTest(arguments):
                with self.assertRaises(McpBadArgument):
                    self.user_env["plm.mcp.tool"]._call_tool("plm_test_tool", arguments)

    def test_a_tool_that_returns_nothing_still_answers(self):
        self.make_tool(code="x = 1")
        result = self.user_env["plm.mcp.tool"]._call_tool("plm_test_tool", {})
        self.assertFalse(result["isError"])
        self.assertIn("successfully", result["content"][0]["text"])

    def test_a_user_error_in_the_code_is_the_answer(self):
        self.make_tool(code="raise UserError('There is nothing to do.')")
        result = self.user_env["plm.mcp.tool"]._call_tool("plm_test_tool", {})
        self.assertTrue(result["isError"])
        self.assertEqual(result["content"][0]["text"], "There is nothing to do.")

    @mute_logger("odoo.addons.plm_mcp.models.plm_mcp_tool")
    def test_a_crash_in_the_code_is_not_shown_to_the_ai(self):
        self.make_tool(code="action = 1 / 0")
        result = self.user_env["plm.mcp.tool"]._call_tool("plm_test_tool", {})
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertIn("The tool failed", text)
        self.assertNotIn("division", text.lower())

    # ------------------------------------------------------------ validation
    def test_the_name_must_be_a_plain_identifier(self):
        for bad in ("", "with space", "dash-ed", "x" * 65):
            with self.subTest(bad), self.assertRaises(ValidationError):
                self.make_tool(bad)

    def test_a_built_in_name_cannot_be_taken(self):
        with self.assertRaises(ValidationError):
            self.make_tool("plm_overview")

    def test_two_enabled_tools_cannot_share_a_name(self):
        self.make_tool("plm_twin")
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.make_tool("plm_twin")

    def test_a_tool_needs_a_description(self):
        with self.assertRaises(ValidationError):
            self.make_tool(plm_mcp_description="   ")

    def test_the_schema_must_be_a_json_object_schema(self):
        bad_schemas = (
            "not json",
            '["a", "list"]',
            '{"type": "array"}',
            '{"properties": []}',
            '{"properties": {"a": "string"}}',
            '{"properties": {"a": {"type": "string"}}, "required": ["b"]}',
        )
        for bad in bad_schemas:
            with self.subTest(bad), self.assertRaises(ValidationError):
                self.make_tool(plm_mcp_schema=bad)

    def test_an_empty_schema_is_a_tool_without_arguments(self):
        self.make_tool(plm_mcp_schema=False)
        tool = next(t for t in self.user_env["plm.mcp.tool"]._list_tools()["tools"]
                    if t["name"] == "plm_test_tool")
        self.assertEqual(tool["inputSchema"],
                         {"type": "object", "properties": {}, "required": []})


@tagged("-standard", "odoo_plm_mcp")
class TestScreenToolsOverHttp(ScreenToolCase, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.make_user(cls, "screen_tool_http")
        cls.token = cls.env["plm.mcp.key"].create({
            "name": "Screen tool key", "user_id": cls.user.id}).key_clear

    def rpc(self, method, params=None):
        return self.url_open(
            "/plm/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                             "params": params or {}}),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer %s" % self.token})

    def test_a_screen_tool_is_listed_and_called_through_the_endpoint(self):
        self.make_tool(plm_mcp_schema=SCHEMA,
                       code="action = {'echo': arguments['text']}")
        listed = self.rpc("tools/list").json()["result"]["tools"]
        self.assertIn("plm_test_tool", [t["name"] for t in listed])

        result = self.rpc("tools/call", {
            "name": "plm_test_tool", "arguments": {"text": "hello"}}).json()["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"], {"echo": "hello"})

    def test_a_wrong_argument_is_a_jsonrpc_error_with_its_own_message(self):
        self.make_tool(plm_mcp_schema=SCHEMA)
        answer = self.rpc("tools/call", {
            "name": "plm_test_tool", "arguments": {"text": 5}}).json()
        self.assertEqual(answer["error"]["code"], -32602)
        self.assertIn("text", answer["error"]["message"])
        self.assertIn("string", answer["error"]["message"])
