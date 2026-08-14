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
"""The tools, asked the questions they exist for.

Each test is one question an engineer actually asks, and the assertion is on
the part of the answer a person would read — a quantity, a revision, a count of
what is missing. Asserting on the whole payload would turn every improvement to
a description into a failing test.

Two things are checked more carefully than the rest, because both have already
been wrong once: that plm_where_used groups by revision rather than merging
revisions together, and that plm_documents finds a drawing through the document
relation rather than through the document type alone.

    odoo --test-tags=odoo_plm_mcp -i plm_mcp -d <database>
"""
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import McpCommon


@tagged("-standard", "odoo_plm_mcp")
class TestTools(McpCommon):

    def setUp(self):
        super().setUp()
        self.parts = self.build_assembly()

    # ------------------------------------------------------------ find a part
    def test_find_a_part_by_code(self):
        found = self.tool.plm_find_part(query="MCPT-PRT-001")
        codes = [part["engineering_code"] for part in found["parts"]]
        self.assertIn("MCPT-PRT-001", codes)

    def test_find_parts_by_material(self):
        """"Give me the steel parts" — the question that started this tool."""
        found = self.tool.plm_find_part(material="Steel")
        codes = [part["engineering_code"] for part in found["parts"]]
        self.assertIn("MCPT-PRT-001", codes)
        self.assertNotIn("MCPT-PRT-002", codes)

    def test_find_reports_the_material_it_matched_on(self):
        found = self.tool.plm_find_part(query="MCPT-PRT-002")
        part = next(p for p in found["parts"]
                    if p["engineering_code"] == "MCPT-PRT-002")
        self.assertEqual(part["engineering_material"], "Aluminium")

    def test_find_nothing_is_an_empty_answer_not_a_failure(self):
        found = self.tool.plm_find_part(query="MCPT-NO-SUCH-THING")
        self.assertEqual(found["count"], 0)
        self.assertEqual(found["parts"], [])

    def test_the_limit_is_reported_when_it_bites(self):
        found = self.tool.plm_find_part(query="MCPT-", limit=1)
        self.assertEqual(len(found["parts"]), 1)
        self.assertTrue(found["truncated"])

    # ---------------------------------------------------------------- detail
    def test_part_detail_answers_is_this_the_current_revision(self):
        detail = self.tool.plm_part_detail(code="MCPT-PRT-001")
        self.assertTrue(detail["is_latest"])
        self.assertTrue(detail["is_first_revision"])
        self.assertIsNone(detail["previous_revision"])

    def test_part_detail_sees_an_older_revision_as_older(self):
        self.new_revision(self.parts["part"])
        detail = self.tool.plm_part_detail(code="MCPT-PRT-001", revision=0)
        self.assertFalse(detail["is_latest"])
        self.assertEqual(len(detail["revisions"]), 2)

    def test_part_detail_lists_the_documents(self):
        detail = self.tool.plm_part_detail(code="MCPT-PRT-001")
        names = [doc["name"] for doc in detail["documents"]]
        self.assertIn("MCPT-PRT-001 model", names)
        self.assertIn("MCPT-PRT-001 sheet", names)

    def test_asking_for_a_part_that_is_not_there(self):
        with self.assertRaises(UserError):
            self.tool.plm_part_detail(code="MCPT-NO-SUCH-CODE")

    # ------------------------------------------------------------------- bom
    def test_walking_the_bom_returns_the_components_with_quantities(self):
        bom = self.tool.plm_bom(code="MCPT-ASM-001")
        self.assertTrue(bom["has_bom"])
        quantities = {line["engineering_code"]: line["quantity"]
                      for line in bom["lines"]}
        self.assertEqual(quantities["MCPT-PRT-001"], 2)
        self.assertEqual(quantities["MCPT-SUB-001"], 1)

    def test_the_bom_goes_down_a_level(self):
        """A component that is itself an assembly carries its own components."""
        bom = self.tool.plm_bom(code="MCPT-ASM-001", depth=3)
        sub = next(line for line in bom["lines"]
                   if line["engineering_code"] == "MCPT-SUB-001")
        children = [line["engineering_code"] for line in sub["components"]]
        self.assertIn("MCPT-PRT-002", children)

    def test_depth_one_stops_at_the_first_level(self):
        bom = self.tool.plm_bom(code="MCPT-ASM-001", depth=1)
        sub = next(line for line in bom["lines"]
                   if line["engineering_code"] == "MCPT-SUB-001")
        self.assertFalse(sub.get("components"))

    def test_a_part_without_a_bom_says_so_and_points_somewhere(self):
        """A dead end that names the next question instead of just ending."""
        bom = self.tool.plm_bom(code="MCPT-PRT-002")
        self.assertFalse(bom["has_bom"])
        self.assertIn("plm_where_used", bom["note"])

    # ------------------------------------------------------------- where used
    def test_where_used_finds_the_parent(self):
        used = self.tool.plm_where_used(code="MCPT-PRT-002")
        parents = [row["engineering_code"]
                   for revision in used["revisions"]
                   for row in revision["used_in"]]
        self.assertIn("MCPT-SUB-001", parents)

    def test_where_used_keeps_revisions_apart(self):
        """The point of the tool: revision 0 and revision 1 are not one answer.

        Merging them would report a part as used in an assembly that only ever
        used its previous revision — which is how a change gets released against
        the wrong parent.
        """
        self.new_revision(self.parts["child"])
        used = self.tool.plm_where_used(code="MCPT-PRT-002")
        revisions = [entry["engineering_revision"] for entry in used["revisions"]]
        self.assertIn(0, revisions)
        self.assertIn(1, revisions)
        newer = next(entry for entry in used["revisions"]
                     if entry["engineering_revision"] == 1)
        self.assertEqual(newer["used_in_count"], 0,
                         "the new revision is not in any BOM yet")

    def test_where_used_counts_the_quantity(self):
        used = self.tool.plm_where_used(code="MCPT-PRT-001")
        row = next(row for revision in used["revisions"]
                   for row in revision["used_in"])
        self.assertEqual(row["quantity"], 2)

    # --------------------------------------------------------------- compare
    def test_comparing_a_bom_with_itself_finds_nothing_changed(self):
        compared = self.tool.plm_compare_bom(
            code_a="MCPT-ASM-001", code_b="MCPT-ASM-001")
        statuses = {row["status"] for row in compared["components"]}
        self.assertEqual(statuses, {"unchanged"})

    def test_a_removed_component_is_reported_as_only_on_one_side(self):
        # Copying the template does not copy its bill of material, so the new
        # revision gets one of its own — with the machined part left out, which
        # is the difference the comparison has to report.
        newer = self.new_revision(self.parts["assembly"])
        self.create_bom(newer, self.parts["sub"], qty=1)

        compared = self.tool.plm_compare_bom(
            code_a="MCPT-ASM-001", revision_a=0,
            code_b="MCPT-ASM-001", revision_b=1)
        by_code = {row["engineering_code"]: row["status"]
                   for row in compared["components"]}
        self.assertEqual(by_code["MCPT-PRT-001"], "only_left")

    def test_compare_echoes_which_revisions_it_compared(self):
        compared = self.tool.plm_compare_bom(
            code_a="MCPT-ASM-001", code_b="MCPT-ASM-001")
        self.assertEqual(compared["compared"]["left"]["engineering_code"],
                         "MCPT-ASM-001")

    # ------------------------------------------------------------- documents
    def test_a_drawing_is_found_through_the_document_relation(self):
        """Not through document_type alone.

        In a real installation the pair is a proprietary model and its sheet,
        and what ties them is the LyTree relation. Detection that trusted the
        type would report every model as a missing drawing.
        """
        documents = self.tool.plm_documents(code="MCPT-ASM-001", depth=3)
        row = next(row for row in documents["components"]
                   if row["engineering_code"] == "MCPT-PRT-001")
        self.assertTrue(row["has_drawing"])
        self.assertTrue(row["signals"]["has_model"])

    def test_what_is_missing_a_drawing(self):
        """The question that decides what still has to be drawn."""
        documents = self.tool.plm_documents(
            code="MCPT-ASM-001", depth=3, missing="drawing")
        codes = [row["engineering_code"] for row in documents["components"]]
        self.assertIn("MCPT-PRT-002", codes)
        self.assertNotIn("MCPT-PRT-001", codes)

    def test_the_totals_are_reported(self):
        documents = self.tool.plm_documents(code="MCPT-ASM-001", depth=3)
        self.assertGreater(documents["totals"]["components"], 0)

    # ----------------------------------------------------------- spare parts
    def test_a_product_without_a_spare_list_says_so(self):
        spare = self.tool.plm_spare_parts(code="MCPT-ASM-001")
        self.assertFalse(spare["has_spare_list"])
        self.assertIn("note", spare)

    # -------------------------------------------------------------- overview
    def test_the_overview_counts_what_is_there(self):
        overview = self.tool.plm_overview()
        self.assertGreaterEqual(overview["parts"]["distinct_codes"], 4)
        self.assertIn("bills_of_material", overview)
        self.assertIn("documents", overview)

    # ------------------------------------------------------------ vocabulary
    def test_the_materials_in_use_are_listed(self):
        materials = self.tool.plm_list_materials()
        values = [entry["value"] for entry in materials["title_block"]]
        self.assertIn("Steel", values)
        self.assertIn("Aluminium", values)

    def test_each_vocabulary_tool_answers_about_its_own_field(self):
        self.assertEqual(self.tool.plm_list_materials()["kind"], "material")
        self.assertIn("kind", self.tool.plm_list_finishings())
        self.assertIn("kind", self.tool.plm_list_treatments())

    # ---------------------------------------------------------------- impact
    def test_change_impact_names_the_assemblies_above(self):
        impact = self.tool.plm_change_impact(code="MCPT-PRT-002")
        self.assertGreaterEqual(impact["impact"][0]["assemblies_count"], 1)
        self.assertIn("flags", impact)

    def test_change_impact_says_when_a_revision_is_already_open(self):
        """The collision this tool exists to prevent."""
        newer = self.new_revision(self.parts["part"])
        newer.engineering_state = "draft"
        impact = self.tool.plm_change_impact(code="MCPT-PRT-001")
        self.assertTrue(impact["flags"]["revision_in_progress"])

    # -------------------------------------------------------------- activity
    def test_what_is_in_progress(self):
        self.parts["part"].engineering_state = "draft"
        progress = self.tool.plm_in_progress(target="parts")
        codes = [row["engineering_code"] for row in progress["parts"]]
        self.assertIn("MCPT-PRT-001", codes)

    def test_recent_releases_is_bounded_by_the_window(self):
        released = self.tool.plm_recent_releases(days=7, target="parts")
        self.assertEqual(released["days"], 7)
        self.assertIn("parts", released)
