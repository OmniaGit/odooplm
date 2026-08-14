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
"""The layer everything else stands on: how tools are found and called.

Nothing here touches PLM data. These are tests of the dispatch itself — a tool
that is not declared, an argument that is missing, an argument that should never
have been passed on — because a fault at this level makes every tool wrong at
once, and does so silently.

    odoo --test-tags=odoo_plm_mcp -i plm_mcp -d <database>
"""
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm_mcp.models.plm_mcp_tool import (
    McpInvalidArguments,
    McpToolNotFound,
    mcp_tool,
)


@tagged("-standard", "odoo_plm_mcp")
class TestRegistry(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool = cls.env["plm.mcp.tool"]

    # ------------------------------------------------------------- discovery
    def test_every_declared_tool_is_found(self):
        """The registry sees the tools of this module, by name."""
        specs = self.tool._tool_specs()
        for name in ("plm_find_part", "plm_part_detail", "plm_bom",
                     "plm_where_used", "plm_compare_bom", "plm_documents",
                     "plm_spare_parts", "plm_overview", "plm_change_impact",
                     "plm_in_progress", "plm_recent_releases",
                     "plm_list_materials", "plm_list_finishings",
                     "plm_list_treatments"):
            self.assertIn(name, specs, "%s is not in the registry" % name)

    def test_a_tool_resolves_to_a_real_method(self):
        """Every spec names a method that exists — a typo would only show here."""
        for name, (method_name, _spec) in self.tool._tool_specs().items():
            self.assertTrue(
                hasattr(self.tool, method_name),
                "tool %s points at %s, which does not exist" % (name, method_name),
            )

    def test_listing_is_complete_and_stable(self):
        """tools/list carries what a model needs, in a repeatable order.

        The order matters beyond tidiness: the list travels in the prompt on
        every conversation, and an unstable one costs a cache hit each time.
        """
        listed = self.tool._list_tools()["tools"]
        self.assertEqual(len(listed), len(self.tool._tool_specs()))
        self.assertEqual([t["name"] for t in listed],
                         sorted(t["name"] for t in listed))
        for entry in listed:
            self.assertTrue(entry["description"].strip(),
                            "%s has no description" % entry["name"])
            self.assertEqual(entry["inputSchema"]["type"], "object")

    def test_descriptions_say_something(self):
        """A description is what routes a question to the right tool.

        The threshold is deliberately low — this catches a placeholder, not
        prose that could be better.
        """
        for name, (_method, spec) in self.tool._tool_specs().items():
            self.assertGreater(
                len(spec["description"]), 80,
                "the description of %s is too short to route anything" % name,
            )

    def test_required_arguments_are_declared_properties(self):
        """A required argument that is not a declared property can never be sent."""
        for name, (_method, spec) in self.tool._tool_specs().items():
            schema = spec["inputSchema"]
            for required in schema["required"]:
                self.assertIn(
                    required, schema["properties"],
                    "%s requires %s but does not declare it" % (name, required),
                )

    # -------------------------------------------------------------- dispatch
    def test_unknown_tool_raises(self):
        """A tool that does not exist is a fault in the request, not a result."""
        with self.assertRaises(McpToolNotFound):
            self.tool._call_tool("plm_does_not_exist", {})

    def test_missing_required_argument_raises(self):
        with self.assertRaises(McpInvalidArguments):
            self.tool._call_tool("plm_part_detail", {})

    def test_undeclared_argument_is_ignored(self):
        """An argument the tool never declared must not reach the method.

        Passing it through would raise TypeError deep inside the call, which the
        client would read as a broken server rather than as its own mistake.
        """
        result = self.tool._call_tool(
            "plm_overview", {"unexpected": "value"})
        self.assertFalse(result["isError"])

    def test_none_arguments_are_dropped(self):
        """A null argument means "not given", and must not override a default.

        This is the regression that matters most in this file. Odoo's own agent
        fills every declared argument with None before calling, so without this
        the default of latest_only would be turned into False on every call from
        the chat — the opposite of what the tool promises.
        """
        both = self.tool._call_tool("plm_find_part", {"query": "MCPT-NOTHING"})
        with_nulls = self.tool._call_tool("plm_find_part", {
            "query": "MCPT-NOTHING",
            "material": None,
            "latest_only": None,
            "limit": None,
        })
        self.assertEqual(both["structuredContent"],
                         with_nulls["structuredContent"])

    # ---------------------------------------------------------------- results
    def test_result_carries_structured_and_text(self):
        """Both shapes travel: clients read one or the other, never both."""
        result = self.tool._call_tool("plm_overview", {})
        self.assertFalse(result["isError"])
        self.assertIn("structuredContent", result)
        self.assertEqual(result["content"][0]["type"], "text")
        self.assertTrue(result["content"][0]["text"])

    def test_a_refusal_is_a_result_not_an_exception(self):
        """"No such part" is an answer the model can act on.

        If it came back as a transport error the agent would report that the
        server is broken, when in fact it answered correctly.
        """
        result = self.tool._call_tool(
            "plm_part_detail", {"code": "MCPT-NO-SUCH-CODE"})
        self.assertTrue(result["isError"])
        self.assertIn("MCPT-NO-SUCH-CODE", result["content"][0]["text"])

    # ------------------------------------------------------------- extension
    def test_the_decorator_is_all_it_takes_to_declare_a_tool(self):
        """What the registry looks for, and nothing more.

        The decorator stamps the spec onto the method; _tool_specs then finds it
        by walking the class dictionaries. This checks the first half directly —
        the second half is proved by every tool of this module being found, and
        by plm_mcp_ecr adding two more from a separate addon.
        """
        @mcp_tool(
            "plm_test_extra",
            "A tool declared in a test, written long enough to look like the "
            "real ones so that the shape being checked is the real shape.",
            properties={"code": {"type": "string"}},
            required=["code"],
        )
        def some_method(self):
            return {"ok": True}

        spec = some_method._mcp_tool
        self.assertEqual(spec["name"], "plm_test_extra")
        self.assertEqual(spec["inputSchema"]["type"], "object")
        self.assertEqual(spec["inputSchema"]["required"], ["code"])
        self.assertIn("code", spec["inputSchema"]["properties"])
        # Stripped, because the descriptions are written as indented docstring
        # blocks and the leading whitespace would travel to the model.
        self.assertFalse(spec["description"].startswith(" "))

    def test_tools_from_a_second_module_join_the_same_registry(self):
        """plm_mcp_ecr declares its tools on the same abstract model.

        Skipped when that module is not installed: it depends on
        activity_validation, and this module does not.
        """
        if not self.env["ir.module.module"].search([
                ("name", "=", "plm_mcp_ecr"), ("state", "=", "installed")]):
            self.skipTest("plm_mcp_ecr is not installed")
        specs = self.tool._tool_specs()
        self.assertIn("plm_change_requests", specs)
        self.assertIn("plm_my_validations", specs)

    def test_user_error_becomes_an_error_result(self):
        """Whatever a tool refuses with, the transport stays intact."""
        result = self.tool._tool_error(str(UserError("refused")))
        self.assertTrue(result["isError"])
