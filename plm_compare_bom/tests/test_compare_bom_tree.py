from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm", "odoo_plm_compare_bom")
class PlmCompareBomTree(TransactionCase, PlmEntityCreator):
    """Multilevel comparison of two BoMs (plm.compare.bom.tree).

    CBT-ASM-001 revision 0
    ├── CBT-PRT-001  x2
    ├── CBT-SUB-001  x1
    │   ├── CBT-PRT-002  x3
    │   └── CBT-SUB-002  x1
    │       └── CBT-PRT-003  x4
    └── VITE-M6  x8   (default_code only, no engineering code)
    """

    def setUp(self):
        super().setUp()
        self.tree = self.env["plm.compare.bom.tree"]
        self.asm = self.create_product_product("Assembly", "CBT-ASM-001")
        self.prt_1 = self.create_product_product("Part 1", "CBT-PRT-001")
        self.sub_1 = self.create_product_product("Sub 1", "CBT-SUB-001")
        self.prt_2 = self.create_product_product("Part 2", "CBT-PRT-002")
        self.sub_2 = self.create_product_product("Sub 2", "CBT-SUB-002")
        self.prt_3 = self.create_product_product("Part 3", "CBT-PRT-003")
        self.screw = self._commercial("Screw M6", "VITE-M6")
        self.bom_asm = self._bom(
            self.asm, [(self.prt_1, 2), (self.sub_1, 1), (self.screw, 8)]
        )
        self.bom_sub_1 = self._bom(self.sub_1, [(self.prt_2, 3), (self.sub_2, 1)])
        self._bom(self.sub_2, [(self.prt_3, 4)])

    # ------------------------------------------------------------- helpers
    def _commercial(self, name, default_code, engineering_code=False, revision=0):
        product = self.create_product_template(name).product_variant_id
        product.write(
            {
                "default_code": default_code,
                "engineering_code": engineering_code,
                "engineering_revision": revision,
            }
        )
        return product

    def _bom(self, product, lines, bom_type="normal"):
        return self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "type": bom_type,
                "bom_line_ids": [
                    (0, 0, {"product_id": component.id, "product_qty": qty})
                    for component, qty in lines
                ],
            }
        )

    def _revision(self, product):
        # A revision is refused while the one below is still in draft
        # (RevisionBaseMixin._fix_previous_revisions_state).
        product.product_tmpl_id.with_context(check=False).engineering_state = (
            "released"
        )
        template = product.product_tmpl_id.copy(
            {
                "engineering_code": product.engineering_code,
                "engineering_revision": product.engineering_revision + 1,
            }
        )
        return template.product_variant_id

    def _row(self, node, label):
        """The row with this engineering code, or this default code when it
        has none."""
        for row in node.get("components", []):
            if (row["engineering_code"] or row["default_code"]) == label:
                return row
        self.fail(
            "%s is not among %s"
            % (
                label,
                [
                    row["engineering_code"] or row["default_code"]
                    for row in node.get("components", [])
                ],
            )
        )

    # --------------------------------------------------------------- tests
    def test_identical_boms_have_no_differences(self):
        node = self.tree.compare_boms(self.bom_asm, self.bom_asm)
        self.assertEqual(
            {row["status"] for row in node["components"]}, {"unchanged"}
        )
        sub = self._row(node, "CBT-SUB-001")
        self.assertTrue(sub["has_components"])
        self.assertNotIn("components", sub)

    def test_a_quantity_changed_three_levels_down_shows_its_path(self):
        sub_2 = self._revision(self.sub_2)
        self._bom(sub_2, [(self.prt_3, 5)])
        sub_1 = self._revision(self.sub_1)
        bom_sub_1 = self._bom(sub_1, [(self.prt_2, 3), (sub_2, 1)])
        bom = self._bom(
            self._revision(self.asm),
            [(self.prt_1, 2), (sub_1, 1), (self.screw, 8)],
        )
        node = self.tree.compare_boms(self.bom_asm, bom)

        self.assertEqual(self._row(node, "CBT-PRT-001")["status"], "unchanged")
        level_1 = self._row(node, "CBT-SUB-001")
        self.assertEqual(level_1["status"], "revision_changed")
        self.assertEqual(
            (level_1["bom_left_id"], level_1["bom_right_id"]),
            (self.bom_sub_1.id, bom_sub_1.id),
        )
        self.assertEqual(self._row(level_1, "CBT-PRT-002")["status"], "unchanged")
        level_2 = self._row(level_1, "CBT-SUB-002")
        self.assertEqual(level_2["status"], "revision_changed")
        level_3 = self._row(level_2, "CBT-PRT-003")
        self.assertEqual(level_3["status"], "qty_changed")
        self.assertEqual(
            (level_3["quantity_left"], level_3["quantity_right"]), (4, 5)
        )

    def test_a_subassembly_on_one_side_only_is_not_walked(self):
        bom = self._bom(self._revision(self.asm), [(self.prt_1, 2), (self.screw, 8)])
        sub = self._row(self.tree.compare_boms(self.bom_asm, bom), "CBT-SUB-001")
        self.assertEqual(sub["status"], "only_left")
        self.assertTrue(sub["has_components"])
        self.assertNotIn("components", sub)

    def test_a_line_without_engineering_code_is_compared_by_product(self):
        bom = self._bom(
            self._revision(self.asm),
            [(self.prt_1, 2), (self.sub_1, 1), (self.screw, 10)],
        )
        screw = self._row(self.tree.compare_boms(self.bom_asm, bom), "VITE-M6")
        self.assertEqual(screw["status"], "qty_changed")
        self.assertFalse(screw["engineering_code"])
        self.assertEqual((screw["quantity_left"], screw["quantity_right"]), (8, 10))

    def test_a_removed_line_without_engineering_code_is_reported(self):
        bom = self._bom(self._revision(self.asm), [(self.prt_1, 2), (self.sub_1, 1)])
        screw = self._row(self.tree.compare_boms(self.bom_asm, bom), "VITE-M6")
        self.assertEqual(screw["status"], "only_left")

    def test_a_dash_is_not_an_engineering_code(self):
        """'-' marks a code still to be given (_compute_eng_code_editable): two
        such products are two components, not two revisions of one."""
        nut = self._commercial("Nut M6", "DADO-M6", "-", 0)
        washer = self._commercial("Washer M6", "ROND-M6", "-", 1)
        node = self.tree.compare_boms(
            self._bom(self.prt_1, [(nut, 1)]), self._bom(self.prt_2, [(washer, 1)])
        )
        self.assertEqual(self._row(node, "DADO-M6")["status"], "only_left")
        self.assertEqual(self._row(node, "ROND-M6")["status"], "only_right")

    def test_repeated_lines_are_summed(self):
        bom = self._bom(
            self._revision(self.asm),
            [(self.prt_1, 2), (self.sub_1, 1), (self.screw, 3), (self.screw, 5)],
        )
        node = self.tree.compare_boms(self.bom_asm, bom)
        self.assertEqual(
            {row["status"] for row in node["components"]}, {"unchanged"}
        )

    def test_each_side_keeps_its_bom_type_down_the_tree(self):
        self._bom(self.sub_1, [(self.prt_2, 1)], "phantom")
        kit = self._bom(
            self.asm, [(self.prt_1, 2), (self.sub_1, 1), (self.screw, 8)], "phantom"
        )
        sub = self._row(self.tree.compare_boms(self.bom_asm, kit), "CBT-SUB-001")
        prt_2 = self._row(sub, "CBT-PRT-002")
        self.assertEqual((prt_2["quantity_left"], prt_2["quantity_right"]), (3, 1))
        self.assertEqual(self._row(sub, "CBT-SUB-002")["status"], "only_left")

    def test_a_missing_bom_on_one_side_is_said(self):
        sub_1 = self._revision(self.sub_1)  # no BoM of its own
        bom = self._bom(
            self._revision(self.asm),
            [(self.prt_1, 2), (sub_1, 1), (self.screw, 8)],
        )
        sub = self._row(self.tree.compare_boms(self.bom_asm, bom), "CBT-SUB-001")
        self.assertEqual(sub["status"], "revision_changed")
        self.assertIn("note", sub)

    def test_max_depth_one_does_not_walk_down(self):
        sub_1 = self._revision(self.sub_1)
        self._bom(sub_1, [(self.prt_2, 7)])
        bom = self._bom(
            self._revision(self.asm),
            [(self.prt_1, 2), (sub_1, 1), (self.screw, 8)],
        )
        node = self.tree.compare_boms(self.bom_asm, bom, max_depth=1)
        self.assertNotIn("components", self._row(node, "CBT-SUB-001"))

    def test_a_cycle_stops(self):
        """mrp forbids a cycle on create (_check_bom_cycle); a bad import does
        not go through it, so the line is written in SQL, after every BoM the
        test creates (each create checks the cycle again)."""
        bom = self._bom(
            self._revision(self.asm),
            [(self.prt_1, 2), (self.sub_1, 1), (self.screw, 9)],
        )
        bom_sub_2 = self.env["mrp.bom"].search(
            [("product_tmpl_id", "=", self.sub_2.product_tmpl_id.id)]
        )
        self.env.cr.execute(
            """INSERT INTO mrp_bom_line
                   (bom_id, product_id, product_qty, product_uom_id, sequence)
               VALUES (%s, %s, 1, %s, 99)""",
            (bom_sub_2.id, self.sub_1.id, self.sub_1.uom_id.id),
        )
        bom_sub_2.invalidate_recordset(["bom_line_ids"])
        node = self.tree.compare_boms(self.bom_asm, bom)  # must return
        self.assertEqual(self._row(node, "VITE-M6")["status"], "qty_changed")
        sub_2 = self._row(self._row(node, "CBT-SUB-001"), "CBT-SUB-002")
        self.assertEqual(
            self._row(sub_2, "CBT-SUB-001")["note"],
            "Already compared higher up: cycle stopped.",
        )

    def test_the_wizard_opens_the_tree(self):
        wizard = (
            self.env["plm.compare.bom"]
            .with_context(active_ids=[self.bom_asm.id, self.bom_sub_1.id])
            .create({})
        )
        action = wizard.action_compare_tree()
        self.assertEqual(action["tag"], "plm_compare_bom_tree")
        self.assertEqual(
            action["params"],
            {"bom_left_id": self.bom_asm.id, "bom_right_id": self.bom_sub_1.id},
        )

    def test_a_level_opens_the_single_level_compare(self):
        action = self.env["plm.compare.bom"].action_compare_level(
            self.bom_asm.id, self.bom_sub_1.id
        )
        wizard = self.env["plm.compare.bom"].browse(action["res_id"])
        self.assertEqual(wizard.bom_id1, self.bom_asm)
        self.assertEqual(wizard.bom_id2, self.bom_sub_1)

    def test_the_screen_gets_both_bills_and_the_tree(self):
        data = self.tree.get_tree_data(self.bom_asm.id, self.bom_sub_1.id)
        self.assertEqual(data["left"]["id"], self.bom_asm.id)
        self.assertEqual(data["right"]["engineering_code"], "CBT-SUB-001")
        self.assertIn("components", data["tree"])

    def test_a_quantity_set_on_the_screen_is_written(self):
        sub_2 = self._revision(self.sub_2)
        self._bom(sub_2, [(self.prt_3, 5)])
        sub_1 = self._revision(self.sub_1)
        self._bom(sub_1, [(self.prt_2, 3), (sub_2, 1)])
        bom = self._bom(
            self._revision(self.asm),
            [(self.prt_1, 2), (sub_1, 1), (self.screw, 8)],
        )
        node = self.tree.compare_boms(self.bom_asm, bom)
        prt_3 = self._row(
            self._row(self._row(node, "CBT-SUB-001"), "CBT-SUB-002"), "CBT-PRT-003"
        )
        self.assertEqual(len(prt_3["line_right_ids"]), 1)
        self.tree.set_line_quantities([[prt_3["line_right_ids"][0], 4]])
        node = self.tree.compare_boms(self.bom_asm, bom)
        sub_2_row = self._row(self._row(node, "CBT-SUB-001"), "CBT-SUB-002")
        self.assertNotIn("components", sub_2_row)

    def test_a_repeated_line_keeps_all_its_bill_lines(self):
        bom = self._bom(
            self._revision(self.asm),
            [(self.prt_1, 2), (self.sub_1, 1), (self.screw, 3), (self.screw, 5)],
        )
        screw = self._row(self.tree.compare_boms(self.bom_asm, bom), "VITE-M6")
        self.assertEqual(len(screw["line_left_ids"]), 1)
        self.assertEqual(len(screw["line_right_ids"]), 2)
