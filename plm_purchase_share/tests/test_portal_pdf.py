# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import base64

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.plm.report.component_report import getEmptyDocument
from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

#
# --test-tags=odoo_plm_portal
#

PDF_CONTENT = base64.b64encode(getEmptyDocument())


@tagged("-standard", "odoo_plm_portal", "post_install", "-at_install")
class PlmPurchasePortalPdf(HttpCase):
    """A vendor downloads from the portal the PDF of the drawings of what was
    bought from them, and nothing else: the backend report route renders as
    the user, and a portal user can read neither products nor attachments."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "PORTAL vendor", "plm_portal_access": "view"}
        )
        cls.stranger = cls.env["res.partner"].create(
            {"name": "PORTAL stranger", "plm_portal_access": "view"}
        )
        cls.vendor_user = cls._portal_user("portal_vendor", cls.vendor)
        cls.stranger_user = cls._portal_user("portal_stranger", cls.stranger)
        cls.part = cls._product("PORTAL-PDF-PART")
        cls.drawing = cls._document("PORTAL-PDF-PART.slddrw", cls.part, PDF_CONTENT)
        cls.model = cls._document("PORTAL-PDF-PART.sldprt", cls.part)
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "order_line": [Command.create({"product_id": cls.part.id})],
            }
        )

    @classmethod
    def _portal_user(cls, login, partner):
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "password": login,
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

    @classmethod
    def _document(cls, name, product, printout=False):
        """document_type is computed from the extension of the file: .slddrw
        is a 2D drawing, .sldprt a native model."""
        document = cls.env["ir.attachment"].create(
            {
                "name": name,
                "engineering_code": name,
                "datas": DUMMY_CONTENT,
                "is_plm": True,
                "printout": printout,
            }
        )
        document.linkedcomponents = product
        document.engineering_state = "released"
        return document

    def _pdf_url(self, product):
        return "/my/plm/product/%s/pdf" % product.id

    # the drawings a user may get

    def test_the_vendor_gets_the_released_drawing(self):
        self.assertEqual(
            self.vendor_user._plm_portal_printouts(self.part), self.drawing
        )

    def test_a_draft_drawing_is_not_given(self):
        self.drawing.engineering_state = "draft"
        self.assertFalse(self.vendor_user._plm_portal_printouts(self.part))

    def test_an_obsoleted_drawing_stays_with_who_bought_it(self):
        self.drawing.engineering_state = "obsoleted"
        self.assertEqual(
            self.vendor_user._plm_portal_printouts(self.part), self.drawing
        )

    def test_a_product_not_bought_from_them_gives_nothing(self):
        self.assertFalse(self.stranger_user._plm_portal_printouts(self.part))

    def test_without_a_level_nothing_is_given(self):
        self.vendor.plm_portal_access = "none"
        self.assertFalse(self.vendor_user._plm_portal_printouts(self.part))

    # the routes

    def test_the_vendor_downloads_the_pdf(self):
        self.authenticate("portal_vendor", "portal_vendor")
        response = self.url_open(self._pdf_url(self.part))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_the_download_button_saves_the_pdf(self):
        self.authenticate("portal_vendor", "portal_vendor")
        shown = self.url_open(self._pdf_url(self.part))
        self.assertTrue(shown.headers["Content-Disposition"].startswith("inline"))
        saved = self.url_open(self._pdf_url(self.part) + "?download=1")
        self.assertTrue(saved.headers["Content-Disposition"].startswith("attachment"))

    def test_the_vendor_views_the_pdf_in_a_page(self):
        self.authenticate("portal_vendor", "portal_vendor")
        response = self.url_open(
            "/my/plm/product/%s/view?order_id=%s" % (self.part.id, self.order.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('src="%s"' % self._pdf_url(self.part), response.text)
        self.assertIn('href="/my/purchase/%s"' % self.order.id, response.text)

    def test_a_stranger_views_nothing(self):
        self.authenticate("portal_stranger", "portal_stranger")
        response = self.url_open("/my/plm/product/%s/view" % self.part.id)
        self.assertEqual(response.status_code, 404)

    def test_a_stranger_gets_not_found(self):
        self.authenticate("portal_stranger", "portal_stranger")
        response = self.url_open(self._pdf_url(self.part))
        self.assertEqual(response.status_code, 404)

    def test_the_order_archive_holds_the_drawing(self):
        self.authenticate("portal_vendor", "portal_vendor")
        response = self.url_open("/my/purchase/%s/download_docs" % self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/zip")

    def test_the_order_page_shows_the_download(self):
        self.authenticate("portal_vendor", "portal_vendor")
        response = self.url_open("/my/purchase/%s" % self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self._pdf_url(self.part) + "?download=1", response.text)
        self.assertIn(
            "/my/plm/product/%s/view?order_id=%s" % (self.part.id, self.order.id),
            response.text,
        )

    # the 3D viewer

    def _viewer_document(self):
        if "has_web3d" not in self.env["ir.attachment"]._fields:
            self.skipTest("plm_web_3d is not installed")
        return self._document("PORTAL-PDF-PART.3mf", self.part)

    def test_the_vendor_opens_the_model_in_3d(self):
        viewer = self._viewer_document()
        url = self.vendor_user._plm_portal_viewer_url(self.part)
        self.assertIn("/plm/show_treejs_model?document_id=%s&" % viewer.id, url)

    def test_a_stranger_gets_no_viewer(self):
        self._viewer_document()
        self.assertFalse(self.stranger_user._plm_portal_viewer_url(self.part))

    def test_a_product_without_a_model_gets_no_viewer(self):
        if "has_web3d" not in self.env["ir.attachment"]._fields:
            self.skipTest("plm_web_3d is not installed")
        self.assertFalse(self.vendor_user._plm_portal_viewer_url(self.part))

    def test_the_order_page_shows_the_viewer(self):
        viewer = self._viewer_document()
        self.authenticate("portal_vendor", "portal_vendor")
        response = self.url_open("/my/purchase/%s" % self.order.id)
        self.assertIn(
            "/plm/show_treejs_model?document_id=%s&amp;" % viewer.id, response.text
        )
        page = self.url_open(self.vendor_user._plm_portal_viewer_url(self.part))
        self.assertEqual(page.status_code, 200)
