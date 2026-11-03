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
                   (bom_id, product_id, product_qty, uom_id, sequence)
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
            {
                "bom_left_id": self.bom_asm.id,
                "bom_right_id": self.bom_sub_1.id,
                "follow_kit_subcontract": False,
            },
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

    # ------------------------------------- kit and subcontracting subassemblies
    def _skip_without_type(self, bom_type):
        if bom_type not in self.env["mrp.bom"]._fields["type"].get_values(self.env):
            self.skipTest("BoM type %s is not available" % bom_type)

    def _types_case(self, name, boms_left, boms_right, top=("normal", "normal")):
        """CBT-TOP-<name> revision 0 and 1, each with CBT-SUB-<name> at its own
        revision under it: {bill type: quantity of CBT-PRT-001} on each side.
        Returns the two top bills."""
        top_0 = self.create_product_product("Top", "CBT-TOP-%s" % name)
        sub_0 = self.create_product_product("Sub", "CBT-SUB-%s" % name)
        for bom_type, qty in boms_left.items():
            self._bom(sub_0, [(self.prt_1, qty)], bom_type)
        sub_1 = self._revision(sub_0)
        for bom_type, qty in boms_right.items():
            self._bom(sub_1, [(self.prt_1, qty)], bom_type)
        return (
            self._bom(top_0, [(sub_0, 1)], top[0]),
            self._bom(self._revision(top_0), [(sub_1, 1)], top[1]),
        )

    def _sub_row(self, name, boms_left, boms_right, follow, top=("normal", "normal")):
        left, right = self._types_case(name, boms_left, boms_right, top)
        node = self.tree.compare_boms(left, right, follow_kit_subcontract=follow)
        return self._row(node, "CBT-SUB-%s" % name)

    def _assert_walked(self, sub, qty_left, qty_right):
        part = self._row(sub, "CBT-PRT-001")
        self.assertEqual(part["status"], "qty_changed")
        self.assertEqual(
            (part["quantity_left"], part["quantity_right"]), (qty_left, qty_right)
        )

    def _assert_not_walked(self, sub):
        self.assertEqual(sub["status"], "revision_changed")
        self.assertFalse(sub.get("components"))

    def test_flag_off_a_kit_under_a_normal_bom_is_noted_and_not_walked(self):
        sub = self._sub_row("A", {"phantom": 1}, {"phantom": 2}, False)
        self._assert_not_walked(sub)
        self.assertFalse(sub["has_components"])
        self.assertIn("Kit", sub["note"])
        self.assertNotIn("bom_type_label", sub)

    def test_flag_off_a_subcontracting_bom_is_noted_and_not_walked(self):
        self._skip_without_type("subcontract")
        sub = self._sub_row("B", {"subcontract": 1}, {"subcontract": 2}, False)
        self._assert_not_walked(sub)
        self.assertIn("Subcontracting", sub["note"])

    def test_flag_off_a_normal_bom_beside_a_kit_is_compared_and_the_kit_noted(self):
        sub = self._sub_row(
            "C", {"normal": 5, "phantom": 1}, {"normal": 6, "phantom": 2}, False
        )
        self._assert_walked(sub, 5, 6)
        self.assertIn("Kit", sub["note"])

    def test_flag_off_normal_bom_only_has_no_note(self):
        sub = self._sub_row("D", {"normal": 1}, {"normal": 2}, False)
        self._assert_walked(sub, 1, 2)
        self.assertNotIn("note", sub)

    def test_flag_on_walks_a_kit_under_a_normal_bom(self):
        sub = self._sub_row("E", {"phantom": 1}, {"phantom": 2}, True)
        self._assert_walked(sub, 1, 2)
        self.assertTrue(sub["has_components"])
        self.assertEqual(sub["bom_type_label"], "Kit")
        self.assertNotIn("note", sub)

    def test_flag_on_walks_a_subcontracting_bom_under_a_normal_bom(self):
        self._skip_without_type("subcontract")
        sub = self._sub_row("F", {"subcontract": 1}, {"subcontract": 2}, True)
        self._assert_walked(sub, 1, 2)
        self.assertEqual(sub["bom_type_label"], "Subcontracting")

    def test_flag_on_kit_against_subcontracting_differ_with_the_same_contents(self):
        """Noted on the parent; the same components are no difference."""
        self._skip_without_type("subcontract")
        sub = self._sub_row("G", {"phantom": 1}, {"subcontract": 1}, True)
        self._assert_not_walked(sub)
        self.assertTrue(sub["bom_types_differ"])
        self.assertTrue(sub["has_components"])
        self.assertIn("Kit", sub["note"])
        self.assertIn("Subcontracting", sub["note"])
        self.assertEqual(sub["bom_type_label"], "Kit / Subcontracting")
        self.assertTrue(sub["bom_left_id"] and sub["bom_right_id"])

    def test_flag_on_normal_against_kit_differ_with_the_same_contents(self):
        sub = self._sub_row("H", {"normal": 1}, {"phantom": 1}, True)
        self._assert_not_walked(sub)
        self.assertTrue(sub["bom_types_differ"])
        self.assertIn("Different BoM type", sub["note"])

    def test_flag_on_bills_of_different_types_compare_their_components(self):
        sub = self._sub_row("S", {"normal": 1}, {"phantom": 2}, True)
        self.assertTrue(sub["bom_types_differ"])
        self.assertIn("Different BoM type", sub["note"])
        self._assert_walked(sub, 1, 2)

    def _visible(self, node):
        """{code: row} of what Only differences shows: the rule of isDifferent
        in compare_bom_tree.js."""
        rows = {}
        for row in node.get("components", []):
            if (
                row["status"] != "unchanged"
                or row.get("components")
                or row.get("note")
            ):
                rows[row["engineering_code"]] = row
                rows.update(self._visible(row))
        return rows

    def _family_schema(self):
        """papa normal          | papa normal
        - figlio normal         | - figlio kit
        -- nipote1              |
                                | -- nipote2 (has a kit)
        -- nipote3              | -- nipote3 (has a normal and a kit)
        -- nipote4 rev 0        | -- nipote4 rev 1
        --- nipote4f1           | --- nipote4f1
        --- nipote4f2           |
                                | --- nipote4f3
        """
        product = self.create_product_product
        nipote1 = product("Nipote 1", "NIPOTE1")
        nipote2 = product("Nipote 2", "NIPOTE2")
        nipote3 = product("Nipote 3", "NIPOTE3")
        figlio1 = product("Nipote4 figlio 1", "NIPOTE4F1")
        figlio2 = product("Nipote4 figlio 2", "NIPOTE4F2")
        figlio3 = product("Nipote4 figlio 3", "NIPOTE4F3")
        self._bom(nipote2, [(self.prt_3, 1)], "phantom")
        self._bom(nipote3, [(self.prt_3, 1)], "normal")
        self._bom(nipote3, [(self.prt_3, 1)], "phantom")
        nipote4_0 = product("Nipote 4", "NIPOTE4")
        self._bom(nipote4_0, [(figlio1, 1), (figlio2, 1)])
        nipote4_1 = self._revision(nipote4_0)
        self._bom(nipote4_1, [(figlio1, 1), (figlio3, 1)])
        figlio_0 = product("Figlio", "FIGLIO")
        self._bom(figlio_0, [(nipote1, 1), (nipote3, 1), (nipote4_0, 1)])
        figlio_1 = self._revision(figlio_0)
        self._bom(figlio_1, [(nipote2, 1), (nipote3, 1), (nipote4_1, 1)], "phantom")
        papa_0 = product("Papa", "PAPA")
        left = self._bom(papa_0, [(figlio_0, 1)])
        right = self._bom(self._revision(papa_0), [(figlio_1, 1)])
        return left, right

    def test_the_schema_of_a_bill_type_difference(self):
        left, right = self._family_schema()
        node = self.tree.compare_boms(left, right, follow_kit_subcontract=True)
        shown = self._visible(node)
        self.assertEqual(
            set(shown),
            {"FIGLIO", "NIPOTE1", "NIPOTE2", "NIPOTE4", "NIPOTE4F2", "NIPOTE4F3"},
        )
        figlio = shown["FIGLIO"]
        self.assertTrue(figlio["bom_types_differ"])
        self.assertEqual(figlio["bom_type_label"], "Normal BoM / Kit")
        self.assertEqual(
            figlio["note"], "Different BoM type: left Normal BoM, right Kit."
        )
        self.assertEqual(shown["NIPOTE1"]["status"], "only_left")
        self.assertEqual(shown["NIPOTE2"]["status"], "only_right")
        self.assertEqual(shown["NIPOTE4"]["status"], "revision_changed")
        self.assertNotIn("bom_types_differ", shown["NIPOTE4"])
        self.assertEqual(shown["NIPOTE4F2"]["status"], "only_left")
        self.assertEqual(shown["NIPOTE4F3"]["status"], "only_right")
        # Compared and the same: there, and not shown.
        self.assertEqual(self._row(figlio, "NIPOTE3")["status"], "unchanged")
        self.assertEqual(
            self._row(shown["NIPOTE4"], "NIPOTE4F1")["status"], "unchanged"
        )

    def test_flag_off_the_schema_stops_at_the_kit(self):
        left, right = self._family_schema()
        shown = self._visible(self.tree.compare_boms(left, right))
        self.assertEqual(set(shown), {"FIGLIO"})
        self.assertIn("Only the left side", shown["FIGLIO"]["note"])

    def test_flag_on_normal_is_walked_and_a_different_kit_beside_it_is_noted(self):
        sub = self._sub_row(
            "I", {"normal": 5, "phantom": 1}, {"normal": 5, "phantom": 2}, True
        )
        self.assertNotIn("components", sub)
        self.assertEqual(sub["note"], "The Kit bills differ too.")
        self.assertNotIn("bom_types_differ", sub)

    def test_flag_on_the_same_kit_beside_a_normal_bill_is_not_noted(self):
        sub = self._sub_row(
            "T", {"normal": 5, "phantom": 1}, {"normal": 6, "phantom": 1}, True
        )
        self._assert_walked(sub, 5, 6)
        self.assertNotIn("note", sub)

    def test_flag_on_max_depth_one_does_not_look_at_the_kit_beside(self):
        left, right = self._types_case(
            "U", {"normal": 5, "phantom": 1}, {"normal": 5, "phantom": 2}
        )
        node = self.tree.compare_boms(
            left, right, max_depth=1, follow_kit_subcontract=True
        )
        row = self._row(node, "CBT-SUB-U")
        self.assertNotIn("note", row)
        self.assertNotIn("_other_common_boms", row)

    def test_flag_on_a_difference_down_a_branch_is_notified_on_its_way_up(self):
        """figlio normal / kit -> ramo rev 0 / rev 1 -> part 1 / 2: every parent
        on the way is shown, the different type only where it is."""
        part = self.create_product_product("Part", "BRANCH-PART")
        ramo_0 = self.create_product_product("Ramo", "BRANCH-RAMO")
        self._bom(ramo_0, [(part, 1)])
        ramo_1 = self._revision(ramo_0)
        self._bom(ramo_1, [(part, 2)])
        figlio_0 = self.create_product_product("Figlio", "BRANCH-FIGLIO")
        self._bom(figlio_0, [(ramo_0, 1)])
        figlio_1 = self._revision(figlio_0)
        self._bom(figlio_1, [(ramo_1, 1)], "phantom")
        top_0 = self.create_product_product("Top", "BRANCH-TOP")
        left = self._bom(top_0, [(figlio_0, 1)])
        right = self._bom(self._revision(top_0), [(figlio_1, 1)])
        shown = self._visible(
            self.tree.compare_boms(left, right, follow_kit_subcontract=True)
        )
        self.assertEqual(
            set(shown), {"BRANCH-FIGLIO", "BRANCH-RAMO", "BRANCH-PART"}
        )
        self.assertTrue(shown["BRANCH-FIGLIO"]["bom_types_differ"])
        self.assertNotIn("bom_types_differ", shown["BRANCH-RAMO"])
        self.assertEqual(shown["BRANCH-PART"]["status"], "qty_changed")

    def test_flag_on_a_revised_leaf_with_another_bill_type_is_shown(self):
        """nipote3 of the schema at two revisions, normal and kit, with the same
        components: the row stays, with no children under it."""
        sub = self._sub_row("V", {"normal": 1}, {"phantom": 1}, True)
        self.assertEqual(sub["status"], "revision_changed")
        self.assertTrue(sub["bom_types_differ"])
        self.assertFalse(sub.get("components"))

    def test_flag_on_the_type_in_common_is_compared_and_the_rest_noted(self):
        sub = self._sub_row("J", {"normal": 5, "phantom": 1}, {"phantom": 2}, True)
        self._assert_walked(sub, 1, 2)
        self.assertNotIn("bom_types_differ", sub)
        self.assertIn("Normal", sub["note"])

    def test_flag_on_a_bom_on_one_side_only_names_its_type(self):
        sub = self._sub_row("K", {}, {"phantom": 2}, True)
        self._assert_not_walked(sub)
        self.assertIn("Only the right side has a Kit", sub["note"])

    def test_flag_on_walks_every_level_through_a_kit(self):
        """normal -> kit -> normal -> part: the type is chosen level by level."""
        deep_0 = self.create_product_product("Deep", "CBT-DEEP-L")
        self._bom(deep_0, [(self.prt_1, 1)], "normal")
        deep_1 = self._revision(deep_0)
        self._bom(deep_1, [(self.prt_1, 2)], "normal")
        kit_0 = self.create_product_product("Kit", "CBT-KIT-L")
        self._bom(kit_0, [(deep_0, 1)], "phantom")
        kit_1 = self._revision(kit_0)
        self._bom(kit_1, [(deep_1, 1)], "phantom")
        top_0 = self.create_product_product("Top", "CBT-TOP-L")
        left = self._bom(top_0, [(kit_0, 1)])
        right = self._bom(self._revision(top_0), [(kit_1, 1)])
        node = self.tree.compare_boms(left, right, follow_kit_subcontract=True)
        deep = self._row(self._row(node, "CBT-KIT-L"), "CBT-DEEP-L")
        self._assert_walked(deep, 1, 2)
        self.assertNotIn("bom_type_label", deep)

    def test_an_unrevised_kit_is_not_a_difference(self):
        """The same product on both sides has the same bills: neither a note
        nor a difference, whatever the flag."""
        self._bom(self.prt_2, [(self.prt_3, 1)], "phantom")
        left = self._bom(self.prt_1, [(self.prt_2, 1)])
        right = self._bom(self.screw, [(self.prt_2, 1)])
        for follow in (False, True):
            node = self.tree.compare_boms(left, right, follow_kit_subcontract=follow)
            row = self._row(node, "CBT-PRT-002")
            self.assertEqual(row["status"], "unchanged")
            self.assertNotIn("note", row)
            self.assertNotIn("components", row)
            self.assertFalse(self.tree._is_different(node))

    def test_a_kit_on_one_side_only_is_flagged_and_not_walked(self):
        self._bom(self.prt_2, [(self.prt_3, 1)], "phantom")
        left = self._bom(self.prt_1, [(self.prt_3, 1)])
        right = self._bom(self.screw, [(self.prt_3, 1), (self.prt_2, 1)])
        node = self.tree.compare_boms(left, right, follow_kit_subcontract=True)
        row = self._row(node, "CBT-PRT-002")
        self.assertEqual(row["status"], "only_right")
        self.assertTrue(row["has_components"])
        self.assertEqual(row["bom_type_label"], "Kit")
        self.assertNotIn("components", row)
        self.assertNotIn("note", row)

    def test_the_flag_counts_only_between_two_normal_boms(self):
        """Kit against kit: a normal bill below is left out, and nothing is
        noted; normal against kit keeps each side on its type."""
        sub = self._sub_row(
            "M", {"normal": 1}, {"normal": 2}, True, top=("phantom", "phantom")
        )
        self._assert_not_walked(sub)
        self.assertFalse(sub["has_components"])
        self.assertNotIn("note", sub)
        sub = self._sub_row(
            "N", {"normal": 1, "phantom": 3}, {"normal": 2, "phantom": 4}, True,
            top=("normal", "phantom"),
        )
        self._assert_walked(sub, 1, 4)
        self.assertNotIn("bom_types_differ", sub)

    def test_the_flag_does_not_touch_a_spare_comparison(self):
        self._skip_without_type("spbom")
        sub = self._sub_row(
            "O", {"phantom": 1}, {"phantom": 2}, True, top=("spbom", "spbom")
        )
        self._assert_not_walked(sub)
        self.assertFalse(sub["has_components"])

    def test_compare_products_stays_on_the_type(self):
        """What plm_mcp calls: no note, no label, no kit walked."""
        left, right = self._types_case("P", {"phantom": 1}, {"phantom": 2})
        node = self.tree.compare_products(
            left.product_tmpl_id.product_variant_id,
            "normal",
            right.product_tmpl_id.product_variant_id,
            "normal",
        )
        sub = self._row(node, "CBT-SUB-P")
        self._assert_not_walked(sub)
        self.assertEqual(
            set(sub) & {"note", "bom_type_label", "bom_types_differ"}, set()
        )

    def test_flag_on_a_cycle_through_a_kit_stops(self):
        left, right = self._types_case("Q", {"phantom": 1}, {"phantom": 2})
        sub_1 = self.env["product.product"].search(
            [("engineering_code", "=", "CBT-SUB-Q"), ("engineering_revision", "=", 1)]
        )
        sub_0 = self.env["product.product"].search(
            [("engineering_code", "=", "CBT-SUB-Q"), ("engineering_revision", "=", 0)]
        )
        for sub in (sub_0, sub_1):
            bom = sub.product_tmpl_id.bom_ids
            self.env.cr.execute(
                """INSERT INTO mrp_bom_line
                       (bom_id, product_id, product_qty, uom_id, sequence)
                   VALUES (%s, %s, 1, %s, 99)""",
                (bom.id, sub.id, sub.uom_id.id),
            )
            bom.invalidate_recordset(["bom_line_ids"])
        node = self.tree.compare_boms(left, right, follow_kit_subcontract=True)
        inner = self._row(self._row(node, "CBT-SUB-Q"), "CBT-SUB-Q")
        self.assertEqual(
            inner["note"], "Already compared higher up: cycle stopped."
        )

    def test_the_wizard_passes_the_flag_and_the_screen_uses_it(self):
        left, right = self._types_case("R", {"phantom": 1}, {"phantom": 2})
        wizard = self.env["plm.compare.bom"].create(
            {"bom_id1": left.id, "bom_id2": right.id, "follow_kit_subcontract": True}
        )
        params = wizard.action_compare_tree()["params"]
        self.assertTrue(params["follow_kit_subcontract"])
        data = self.tree.get_tree_data(
            params["bom_left_id"],
            params["bom_right_id"],
            params["follow_kit_subcontract"],
        )
        self._assert_walked(self._row(data["tree"], "CBT-SUB-R"), 1, 2)
        data = self.tree.get_tree_data(left.id, right.id)
        self._assert_not_walked(self._row(data["tree"], "CBT-SUB-R"))

    def test_the_screen_says_when_the_two_bills_are_of_different_types(self):
        kit = self._bom(self.asm, [(self.prt_1, 2)], "phantom")
        other = self._bom(self.prt_1, [(self.prt_2, 1)])
        data = self.tree.get_tree_data(self.bom_asm.id, kit.id)
        self.assertTrue(data["bom_types_differ"])
        data = self.tree.get_tree_data(self.bom_asm.id, other.id)
        self.assertFalse(data["bom_types_differ"])
