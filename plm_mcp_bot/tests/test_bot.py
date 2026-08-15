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
"""The commands, typed the way they actually arrive.

The message reaching the bot is lowercased and still wrapped in HTML, so the
tests feed exactly that rather than a tidy string: getting this wrong is the
one mistake that makes the whole module silently do nothing.

    odoo --test-tags=odoo_plm_mcp -i plm_mcp_bot -d <database>
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm_mcp")
class TestBot(TransactionCase, PlmEntityCreator):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bot = cls.env["plm.mcp.bot"]

    def setUp(self):
        super().setUp()
        self.assembly = self.create_product_product("Assembly", "MCPB-ASM-001")
        self.part = self.create_product_product("Part", "MCPB-PRT-001")
        self.create_bom(self.assembly, self.part, qty=4)

    def posted(self, text):
        """What message_post hands to the bot: lowercased, still HTML."""
        return "<p>%s</p>" % text.lower()

    # ------------------------------------------------------------- recognition
    def test_a_plm_message_is_recognised_through_its_markup(self):
        self.assertTrue(self.bot._command_text(self.posted("/plm bom X")))

    def test_anything_else_is_left_alone(self):
        """Whatever is not ours must reach super() untouched."""
        self.assertFalse(self.bot._command_text(self.posted("hello there")))
        self.assertFalse(self.bot._command_text("<p>where is /plm used?</p>"))
        self.assertFalse(self.bot._command_text(""))

    # -------------------------------------------------------------------- help
    def test_the_bare_prefix_answers_with_the_commands(self):
        answer = self.bot._answer(self.bot._command_text(self.posted("/plm")))
        for command in ("bom", "parte", "dove", "impatto", "mancanti", "aperti"):
            self.assertIn(command, answer)

    def test_an_unknown_command_says_so_and_helps(self):
        answer = self.bot._answer("/plm sbagliato")
        self.assertIn("sbagliato", answer)
        self.assertIn("bom", answer)

    def test_a_command_without_its_argument_says_what_is_missing(self):
        answer = self.bot._answer("/plm bom")
        self.assertIn("codice", answer)

    # ---------------------------------------------------------------- commands
    def test_bom_lists_the_components(self):
        answer = self.bot._answer(
            self.bot._command_text(self.posted("/plm bom MCPB-ASM-001")))
        self.assertIn("MCPB-PRT-001", answer)
        self.assertIn("4", answer)

    def test_a_code_typed_in_lowercase_still_matches(self):
        """The body arrives lowercased, and the codes are not."""
        answer = self.bot._answer(
            self.bot._command_text(self.posted("/plm bom mcpb-asm-001")))
        self.assertIn("MCPB-PRT-001", answer)

    def test_a_part_without_a_bom_is_told_plainly(self):
        answer = self.bot._answer("/plm bom MCPB-PRT-001")
        self.assertNotIn("<table", answer)

    def test_an_unknown_code_answers_instead_of_failing(self):
        answer = self.bot._answer("/plm parte MCPB-NO-SUCH-CODE")
        self.assertIn("MCPB-NO-SUCH-CODE", answer)

    def test_where_used_names_the_parent(self):
        answer = self.bot._answer("/plm dove MCPB-PRT-001")
        self.assertIn("MCPB-ASM-001", answer)

    def test_impact_reports_the_flags(self):
        answer = self.bot._answer("/plm impatto MCPB-PRT-001")
        self.assertIn("MCPB-PRT-001", answer)

    def test_what_is_open_answers_even_when_nothing_is(self):
        self.assertTrue(self.bot._answer("/plm aperti"))

    # --------------------------------------------------------------- arguments
    def test_named_arguments_reach_the_tool(self):
        arguments, unnamed = self.bot._parse_arguments(["BASE-100", "depth=3"])
        self.assertEqual(unnamed, ["BASE-100"])
        self.assertEqual(arguments, {"depth": 3})

    def test_booleans_typed_in_a_chat_are_booleans(self):
        arguments, _unnamed = self.bot._parse_arguments(["latest_only=false"])
        self.assertIs(arguments["latest_only"], False)

    def test_the_help_follows_the_command_table(self):
        """Add a command, and the help says so without being edited."""
        answer = self.bot._answer("/plm")
        for name in self.bot._commands():
            self.assertIn(name, answer)
