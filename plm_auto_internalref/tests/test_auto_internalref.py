from odoo.tests.common import TransactionCase, tagged

from odoo.addons.plm_auto_internalref.hooks import set_manual_internal_references


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

    def test_create_computes_the_reference(self):
        template = self._template("AUTO-A")
        self.assertTrue(template.auto_default_code)
        self.assertEqual(template.default_code, "AUTO-A_0")
        self.assertEqual(template.product_variant_id.default_code, "AUTO-A_0")

    def test_multi_write_gives_each_template_its_own_reference(self):
        templates = self._template("AUTO-A") | self._template("AUTO-B")
        templates.write({"description": "two templates"})
        self.assertEqual(templates.mapped("default_code"), ["AUTO-A_0", "AUTO-B_0"])
        templates.write({"default_code": "BOTH"})
        self.assertEqual(templates.mapped("default_code"), ["AUTO-A_0", "AUTO-B_0"])

    def test_a_manual_reference_is_refused_while_computed(self):
        template = self._template("AUTO-A")
        template.write({"default_code": "MANUAL"})
        self.assertEqual(template.default_code, "AUTO-A_0")
        template.product_variant_id.write({"default_code": "MANUAL"})
        self.assertEqual(template.product_variant_id.default_code, "AUTO-A_0")

    def test_a_manual_reference_stays_once_unset(self):
        template = self._template("AUTO-A")
        template.write({"auto_default_code": False})
        template.write({"default_code": "MANUAL"})
        self.assertEqual(template.default_code, "MANUAL")
        template.write({"description": "another write"})
        self.assertEqual(template.default_code, "MANUAL")
        self.assertEqual(template.product_variant_id.default_code, "MANUAL")

    def test_setting_it_again_computes_the_reference(self):
        template = self._template("AUTO-A")
        template.write({"auto_default_code": False, "default_code": "MANUAL"})
        self.assertEqual(template.default_code, "MANUAL")
        template.write({"auto_default_code": True})
        self.assertEqual(template.default_code, "AUTO-A_0")

    def test_the_variant_flag_is_the_template_one(self):
        template = self._template("AUTO-A")
        variant = template.product_variant_id
        variant.write({"auto_default_code": False, "default_code": "MANUAL"})
        self.assertFalse(template.auto_default_code)
        self.assertEqual(template.default_code, "MANUAL")
        variant.write({"auto_default_code": True})
        self.assertEqual(variant.default_code, "AUTO-A_0")

    def test_a_template_without_engineering_code_is_left_alone(self):
        template = self.env["product.template"].create(
            {"name": "no code", "default_code": "FREE"}
        )
        self.assertEqual(template.default_code, "FREE")
        template.write({"default_code": "FREE-2"})
        self.assertEqual(template.default_code, "FREE-2")

    def test_a_new_revision_gets_its_reference(self):
        variant = self._template("AUTO-REV").product_variant_id
        variant.action_confirm()
        variant.action_release()
        new_id, revision = variant.NewRevision()
        self.assertEqual(revision, 1)
        self.assertEqual(
            self.env["product.product"].browse(new_id).default_code, "AUTO-REV_1"
        )

    def test_install_keeps_the_manual_references_editable(self):
        computed = self._template("AUTO-A")
        manual = self._template("AUTO-B")
        # a reference written by hand before the module had the flag
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE product_product SET default_code = 'MANUAL' WHERE id = %s",
            (manual.product_variant_id.id,),
        )
        self.env.cr.execute(
            "UPDATE product_template SET default_code = 'MANUAL' WHERE id = %s",
            (manual.id,),
        )
        self.env.invalidate_all()
        set_manual_internal_references(self.env)
        self.assertTrue(computed.auto_default_code)
        self.assertFalse(manual.auto_default_code)
