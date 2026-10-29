from odoo.tests import HttpCase, tagged

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm", "odoo_plm_compare_bom", "post_install", "-at_install")
class PlmCompareBomTreeTour(HttpCase, PlmEntityCreator):
    def _bom(self, product, lines):
        return self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "type": "normal",
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
