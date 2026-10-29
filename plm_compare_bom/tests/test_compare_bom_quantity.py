from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm", "odoo_plm_compare_bom")
class PlmCompareBomQuantity(TransactionCase, PlmEntityCreator):
    """A quantity edited in the single level comparison is saved on its bill
    line, except in the summarized comparison, whose rows sum lines."""

    def setUp(self):
        super().setUp()
        self.part = self.create_product_product("Part", "CBQ-PRT-001")
        self.bom_1 = self._bom("CBQ-ASM-001", 4)
        self.bom_2 = self._bom("CBQ-ASM-002", 5)

    def _bom(self, code, quantity):
        parent = self.create_product_product(code, code)
        return self.env["mrp.bom"].create(
            {
                "product_tmpl_id": parent.product_tmpl_id.id,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": self.part.id, "product_qty": quantity})
                ],
            }
        )

    def _compare(self, compute_type):
        wizard = self.env["plm.compare.bom"].create(
            {
                "bom_id1": self.bom_1.id,
                "bom_id2": self.bom_2.id,
                "compute_type": compute_type,
            }
        )
        wizard.action_compare_Bom()
        return wizard

    def test_a_quantity_edited_is_saved(self):
        wizard = self._compare("num_qty")
        wizard.anotinb.itemqty = 5
        wizard.update_bom()
        self.assertEqual(self.bom_1.bom_line_ids.product_qty, 5)
        self.assertEqual(self.bom_2.bom_line_ids.product_qty, 5)

    def test_a_summarized_quantity_is_not_saved(self):
        wizard = self._compare("summarized")
        wizard.bnotina.itemqty = 3
        wizard.update_bom()
        self.assertEqual(self.bom_1.bom_line_ids.product_qty, 4)
        self.assertEqual(self.bom_2.bom_line_ids.product_qty, 5)
