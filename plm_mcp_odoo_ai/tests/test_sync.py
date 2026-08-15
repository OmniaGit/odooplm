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
"""The bridge: the same tools, published where Odoo's own agent can see them.

These tests only run where Odoo Enterprise is installed — without the ai module
this one cannot be installed either, so nothing here is skipped at runtime.

What matters is that nothing is written twice. The server actions are generated
from the same registry the MCP endpoint reads, so the test asserts the
correspondence rather than the contents: one action per tool, named as the tool,
carrying the tool's own description and schema.

    odoo --test-tags=odoo_plm_mcp -i plm_mcp_odoo_ai -d <database>
"""
import json

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-standard", "odoo_plm_mcp")
class TestSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool = cls.env["plm.mcp.tool"]
        cls.specs = cls.tool._tool_specs()

    def action_for(self, tool_name):
        return self.env.ref("plm_mcp_odoo_ai.%s" % tool_name,
                            raise_if_not_found=False)

    def test_every_tool_has_an_action(self):
        """One per tool, no more and no less."""
        for tool_name in self.specs:
            self.assertTrue(
                self.action_for(tool_name),
                "no server action was generated for %s" % tool_name,
            )

    def test_the_external_id_is_the_tool_name(self):
        """It is the name the model calls the tool by, not a label.

        Registered under any other id, the agent would be offered something like
        "action_412" and would have no reason to pick it.
        """
        action = self.action_for("plm_find_part")
        self.assertEqual(action.name, "plm_find_part")

    def test_the_action_is_offered_to_the_agent(self):
        action = self.action_for("plm_find_part")
        self.assertTrue(action.use_in_ai)
        self.assertEqual(action.state, "code")

    def test_the_description_is_the_tools_own(self):
        """The description is what routes a question; it must not be rewritten."""
        for tool_name, (_method, spec) in self.specs.items():
            action = self.action_for(tool_name)
            self.assertEqual(action.ai_tool_description, spec["description"])

    def test_the_schema_is_the_tools_own(self):
        for tool_name, (_method, spec) in self.specs.items():
            action = self.action_for(tool_name)
            self.assertEqual(json.loads(action.ai_tool_schema),
                             spec["inputSchema"])

    def test_the_generated_code_calls_the_registry(self):
        """One line, delegating — the tool itself is not reimplemented here."""
        action = self.action_for("plm_part_detail")
        self.assertIn("_call_tool", action.code)
        self.assertIn("'plm_part_detail'", action.code)
        self.assertIn("ai['result']", action.code)

    def test_every_declared_argument_is_passed(self):
        """Odoo hands each declared argument to the code as a variable.

        They are all passed on, empty ones included, because _call_tool is what
        drops the empty ones — dropping them here instead would need this module
        to know each tool's defaults.
        """
        spec = self.specs["plm_find_part"][1]
        code = self.action_for("plm_find_part").code
        for argument in spec["inputSchema"]["properties"]:
            self.assertIn("'%s': %s" % (argument, argument), code)

    def test_syncing_again_changes_nothing(self):
        """Idempotent, because it runs on every module update."""
        before = self.action_for("plm_overview")
        self.tool._sync_odoo_ai_tools()
        after = self.action_for("plm_overview")
        self.assertEqual(before, after)

    def test_syncing_claims_every_external_id(self):
        """The actions have to survive the end of a module load.

        Odoo deletes records whose external id belongs to a module being
        updated and was not seen during that load (ir_model.py, _process_end).
        The sync therefore registers every id on every run, not only when it
        creates the action — the first version claimed them only on creation,
        so a plain -u dropped all fourteen and the agent lost its tools with no
        error anywhere.
        """
        self.tool._sync_odoo_ai_tools()
        loaded = self.env.registry.loaded_xmlids
        for tool_name in self.specs:
            self.assertIn(
                "plm_mcp_odoo_ai.%s" % tool_name, loaded,
                "%s was not claimed and would be deleted on update" % tool_name,
            )

    def test_the_tools_are_gathered_in_a_topic(self):
        topic = self.env.ref("plm_mcp_odoo_ai.ai_topic_plm",
                             raise_if_not_found=False)
        self.assertTrue(topic, "the PLM topic was not created")
        self.assertEqual(len(topic.tool_ids), len(self.specs))
