from odoo.tests import HttpCase, tagged

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm", "odoo_plm_compare_bom", "post_install", "-at_install")
class PlmCompareBomTreeTour(HttpCase, PlmEntityCreator):
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
        return product.product_tmpl_id.copy(
            {
                "engineering_code": product.engineering_code,
                "engineering_revision": product.engineering_revision + 1,
            }
        ).product_variant_id

    def test_the_tree_screen(self):
        """CBT-PRT-003 goes from 4 to 5 under CBT-SUB-002 under CBT-SUB-001:
        the screen opens on that path alone."""
        asm = self.create_product_product("Assembly", "CBT-ASM-001")
        prt_1 = self.create_product_product("Part 1", "CBT-PRT-001")
        sub_1 = self.create_product_product("Sub 1", "CBT-SUB-001")
        sub_2 = self.create_product_product("Sub 2", "CBT-SUB-002")
        prt_3 = self.create_product_product("Part 3", "CBT-PRT-003")
        left = self._bom(asm, [(prt_1, 2), (sub_1, 1)])
        self._bom(sub_1, [(sub_2, 1)])
        self._bom(sub_2, [(prt_3, 4)])
        sub_2_rev = self._revision(sub_2)
        self._bom(sub_2_rev, [(prt_3, 5)])
        sub_1_rev = self._revision(sub_1)
        self._bom(sub_1_rev, [(sub_2_rev, 1)])
        sub_3 = self.create_product_product("Sub 3", "CBT-SUB-003")
        self._bom(sub_3, [(prt_3, 1)])
        right = self._bom(
            self._revision(asm), [(prt_1, 2), (sub_1_rev, 1), (sub_3, 1)]
        )

        wizard = self.env["plm.compare.bom"].create(
            {"bom_id1": left.id, "bom_id2": right.id}
        )
        self.start_tour(
            "/odoo/plm.compare.bom/%s" % wizard.id,
            "plm_compare_bom_tree_tour",
            login="admin",
        )

    def test_the_flag_walks_a_kit_on_the_screen(self):
        """CBT-SUB-001 is a kit going from 1 to 2 of CBT-PRT-003: the row of the
        part appears only with the flag of the wizard."""
        asm = self.create_product_product("Assembly", "CBT-ASM-001")
        sub_1 = self.create_product_product("Sub 1", "CBT-SUB-001")
        prt_3 = self.create_product_product("Part 3", "CBT-PRT-003")
        self._bom(sub_1, [(prt_3, 1)], "phantom")
        sub_1_rev = self._revision(sub_1)
        self._bom(sub_1_rev, [(prt_3, 2)], "phantom")
        left = self._bom(asm, [(sub_1, 1)])
        right = self._bom(self._revision(asm), [(sub_1_rev, 1)])
        wizard = self.env["plm.compare.bom"].create(
            {"bom_id1": left.id, "bom_id2": right.id}
        )
        self.start_tour(
            "/odoo/plm.compare.bom/%s" % wizard.id,
            "plm_compare_bom_tree_kit_tour",
            login="admin",
        )

    def test_the_schema_of_a_bill_type_difference_on_the_screen(self):
        """The rows of the schema of test_compare_bom_tree: the same components
        hidden, the type on the parent."""
        product = self.create_product_product
        nipote1 = product("Nipote 1", "NIPOTE1")
        nipote2 = product("Nipote 2", "NIPOTE2")
        nipote3 = product("Nipote 3", "NIPOTE3")
        figlio1 = product("Nipote4 figlio 1", "NIPOTE4F1")
        figlio2 = product("Nipote4 figlio 2", "NIPOTE4F2")
        figlio3 = product("Nipote4 figlio 3", "NIPOTE4F3")
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
        wizard = self.env["plm.compare.bom"].create(
            {"bom_id1": left.id, "bom_id2": right.id}
        )
        self.start_tour(
            "/odoo/plm.compare.bom/%s" % wizard.id,
            "plm_compare_bom_tree_schema_tour",
            login="admin",
        )

    def test_the_header_says_the_two_types_differ(self):
        """A normal and a kit BoM with the same components: nothing differs
        below, and yet they are not identical."""
        asm = self.create_product_product("Assembly", "CBT-ASM-001")
        prt_1 = self.create_product_product("Part 1", "CBT-PRT-001")
        wizard = self.env["plm.compare.bom"].create(
            {
                "bom_id1": self._bom(asm, [(prt_1, 2)]).id,
                "bom_id2": self._bom(asm, [(prt_1, 2)], "phantom").id,
            }
        )
        self.start_tour(
            "/odoo/plm.compare.bom/%s" % wizard.id,
            "plm_compare_bom_tree_header_tour",
            login="admin",
        )
