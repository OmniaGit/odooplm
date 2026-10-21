from odoo.tests.common import TransactionCase, tagged


@tagged("-standard", "odoo_plm_auto_internalref")
class TestAutoInternalref(TransactionCase):
    """The internal reference computed from the engineering code and revision"""

    def _template(self, engineering_code):
        return self.env["product.template"].create(
            {"name": engineering_code, "engineering_code": engineering_code}
        )

    def test_variant_write_reaches_the_other_modules(self):
        """The variant write goes on to the write of plm (and of product, stock,
        mrp...), which used to be skipped: plm gives an empty description a dot"""
        variant = self._template("AUTO-WRITE").product_variant_id
        variant.write({"description": False})
        self.assertEqual(str(variant.description), "<p>.</p>")
