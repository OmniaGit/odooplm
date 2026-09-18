# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

#
# --test-tags=odoo_plm_portal
#


@tagged("-standard", "odoo_plm_portal", "post_install", "-at_install")
class PlmPortalScope(TransactionCase):
    """What a customer or a vendor reaches of the PLM documents from the
    portal: what is on their own order lines, in the revision that was sold or
    bought, plus the spare parts when they are allowed, and never the native
    CAD file."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "PORTAL customer"})
        cls.stranger = cls.env["res.partner"].create({"name": "PORTAL stranger"})
        cls.portal_user = cls._portal_user("portal_customer", cls.customer)
        cls.stranger_user = cls._portal_user("portal_stranger", cls.stranger)
        cls.machine = cls._product("PORTAL-MACHINE")
        cls.spare = cls._product("PORTAL-SPARE")
        cls.deep_spare = cls._product("PORTAL-SPARE-2")
        cls.secret = cls._product("PORTAL-SECRET")

    @classmethod
    def _portal_user(cls, login, partner):
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "partner_id": partner.id,
                "group_ids": [Command.set(cls.env.ref("base.group_portal").ids)],
            }
        )

    @classmethod
    def _product(cls, code):
        template = cls.env["product.template"].create(
            {"name": code, "engineering_code": code}
        )
        return template.product_variant_id

    def _document(self, name, product, printout=False):
        """document_type is computed from the extension of the file, so the
        names here are the ones the CAD client would give: .slddrw is a 2D
        drawing, .sldprt a native model, .3mf what the viewer shows."""
        document = self.env["ir.attachment"].create(
            {
                "name": name,
                "engineering_code": name,
                "datas": DUMMY_CONTENT,
                "is_plm": True,
                "printout": DUMMY_CONTENT if printout else False,
            }
        )
        document.linkedcomponents = product
        return document

    def _sell(self, product, partner):
        return self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [Command.create({"product_id": product.id})],
            }
        )

    # the level

    def test_the_level_comes_from_the_partner(self):
        self.assertEqual(self.portal_user._plm_portal_access_level(), "none")
        self.customer.plm_portal_access = "view"
        self.assertEqual(self.portal_user._plm_portal_access_level(), "view")
        self.assertFalse(self.portal_user._plm_portal_can_markup())
        self.customer.plm_portal_access = "markup"
        self.assertTrue(self.portal_user._plm_portal_can_markup())

    def test_one_user_can_be_given_another_level(self):
        self.customer.plm_portal_access = "markup"
        other = self._portal_user("portal_customer_2", self.customer)
        other.plm_portal_access = "none"
        self.assertEqual(other._plm_portal_access_level(), "none")
        self.assertEqual(self.portal_user._plm_portal_access_level(), "markup")

    # the scope

    def test_a_customer_sees_what_was_sold_to_them(self):
        self.customer.plm_portal_access = "view"
        self._sell(self.machine, self.customer)
        self._sell(self.secret, self.stranger)
        products = self.portal_user._plm_portal_products()
        self.assertIn(self.machine, products)
        self.assertNotIn(self.secret, products)

    def test_without_a_level_nothing_is_in_scope(self):
        self._sell(self.machine, self.customer)
        self.assertFalse(self.portal_user._plm_portal_products())

    def test_the_sold_revision_stays_in_scope(self):
        """A revision is a product of its own: the order line pins the one that
        was sold, and a newer one does not take its place."""
        self.customer.plm_portal_access = "view"
        self._sell(self.machine, self.customer)
        # A revision is only made of a released one (the revision chain rule).
        self.machine.product_tmpl_id.engineering_state = "released"
        revision = self.machine.product_tmpl_id._new_version().product_variant_id
        products = self.portal_user._plm_portal_products()
        self.assertIn(self.machine, products)
        self.assertNotIn(revision, products)

    def test_the_spare_parts_of_what_was_sold(self):
        if "spbom" not in dict(self.env["mrp.bom"]._fields["type"].selection):
            self.skipTest("plm_spare is not installed")
        self.customer.plm_portal_access = "view"
        self._sell(self.machine, self.customer)
        self._spare_bom(self.machine, self.spare)
        self._spare_bom(self.spare, self.deep_spare)
        self.assertNotIn(self.spare, self.portal_user._plm_portal_products())
        self.customer.plm_portal_spares = True
        products = self.portal_user._plm_portal_products()
        self.assertIn(self.spare, products, "the spare part of the machine")
        self.assertIn(self.deep_spare, products, "and the one below it")

    def _spare_bom(self, parent, child):
        return self.env["mrp.bom"].create(
            {
                "product_tmpl_id": parent.product_tmpl_id.id,
                "type": "spbom",
                "bom_line_ids": [Command.create({"product_id": child.id})],
            }
        )

    def test_a_subcontractor_sees_what_is_under_what_they_make(self):
        """mrp_subcontracting is where Odoo says who makes what: the components
        of those bills of materials, at every level, and nothing else."""
        boms = self.env["mrp.bom"]
        if "subcontractor_ids" not in boms._fields:
            self.skipTest("mrp_subcontracting is not installed")
        vendor = self.env["res.partner"].create({"name": "PORTAL subcontractor"})
        vendor.plm_portal_access = "view"
        vendor_user = self._portal_user("portal_subcontractor", vendor)
        part = self._product("PORTAL-PART")
        screw = self._product("PORTAL-SCREW")
        assembly_bom = boms.create(
            {
                "product_tmpl_id": self.machine.product_tmpl_id.id,
                "subcontractor_ids": [Command.set(vendor.ids)],
                "bom_line_ids": [Command.create({"product_id": part.id})],
            }
        )
        self.assertTrue(assembly_bom)
        boms.create(
            {
                "product_tmpl_id": part.product_tmpl_id.id,
                "bom_line_ids": [Command.create({"product_id": screw.id})],
            }
        )
        products = vendor_user._plm_portal_products()
        self.assertIn(part, products, "what they assemble")
        self.assertIn(screw, products, "and what is under it")
        self.assertNotIn(self.secret, products)

    # the formats

    def test_the_native_cad_file_is_never_given(self):
        native = self._document("PORTAL-1.sldprt", self.machine)
        self.assertFalse(self.portal_user._plm_portal_document_policy(native))

    def test_the_viewer_file_and_the_drawing_pdf(self):
        viewer = self._document("PORTAL-1.3mf", self.machine)
        drawing = self._document("PORTAL-1.slddrw", self.machine, printout=True)
        self.assertEqual(
            self.portal_user._plm_portal_document_policy(viewer), {"view3d"}
        )
        self.assertEqual(
            self.portal_user._plm_portal_document_policy(drawing), {"pdf"}
        )

    def test_a_drawing_without_its_pdf_is_not_given(self):
        drawing = self._document("PORTAL-2.slddrw", self.machine)
        self.assertFalse(self.portal_user._plm_portal_document_policy(drawing))

    # the two together

    def test_what_a_customer_may_get(self):
        self.customer.plm_portal_access = "view"
        self._sell(self.machine, self.customer)
        viewer = self._document("PORTAL-3.3mf", self.machine)
        native = self._document("PORTAL-3.sldprt", self.machine)
        other = self._document("PORTAL-4.3mf", self.secret)
        self.assertTrue(self.portal_user._plm_portal_may(viewer, "view3d"))
        self.assertFalse(self.portal_user._plm_portal_may(viewer, "pdf"))
        self.assertFalse(self.portal_user._plm_portal_may(native, "view3d"))
        self.assertFalse(self.portal_user._plm_portal_may(other, "view3d"))
        self.assertFalse(self.stranger_user._plm_portal_may(viewer, "view3d"))

    def test_the_documents_of_the_scope(self):
        self.customer.plm_portal_access = "view"
        self._sell(self.machine, self.customer)
        viewer = self._document("PORTAL-5.3mf", self.machine)
        self._document("PORTAL-5.sldprt", self.machine)
        self.assertEqual(self.portal_user._plm_portal_documents(), viewer)
