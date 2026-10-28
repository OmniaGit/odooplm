from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm", "odoo_plm_compare_bom")
class PlmCompareBomSummarized(TransactionCase, PlmEntityCreator):
    """Compare Product Quantity (compute_type 'summarized') sums the lines of
    the same product before comparing them."""

    def setUp(self):
        super().setUp()
        self.parent_1 = self.create_product_product("CMP_PARENT_1")
        self.parent_2 = self.create_product_product("CMP_PARENT_2")
        self.child = self.create_product_product("CMP_CHILD")

    def _bom(self, parent, quantities):
        for qty in quantities:
            bom = self.create_bom(parent, self.child, qty)
        return bom

    def _compare(self, bom_1, bom_2):
        wizard = (
            self.env["plm.compare.bom"]
            .with_context(active_ids=[bom_1.id, bom_2.id])
            .create({"compute_type": "summarized"})
        )
        wizard.action_compare_Bom()
        return wizard

    def test_split_lines_same_total(self):
        """2 + 3 on one side and 5 on the other are the same quantity."""
        wizard = self._compare(
            self._bom(self.parent_1, [2, 3]), self._bom(self.parent_2, [5])
        )
        self.assertFalse(wizard.anotinb)
        self.assertFalse(wizard.bnotina)

    def test_split_lines_different_total(self):
        """2 + 3 against 4: one difference of 1 on the first BoM."""
        wizard = self._compare(
            self._bom(self.parent_1, [2, 3]), self._bom(self.parent_2, [4])
        )
        self.assertEqual(wizard.anotinb.mapped("itemqty"), [1.0])
        self.assertEqual(wizard.anotinb.reason, "changed_qty")
        self.assertFalse(wizard.bnotina)
