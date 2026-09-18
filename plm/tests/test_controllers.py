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
import base64

from odoo import Command
from odoo.tests import HttpCase, tagged

#
# --test-tags=odoo_plm_permission_levels
#

# A one pixel png, so that image_response answers with an image.
PIXEL = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYAAAAAY"
        "AAjCB0C8AAAAASUVORK5CYII="
    )
)


@tagged("-standard", "odoo_plm_permission_levels", "post_install", "-at_install")
class PlmPreviewRoutes(HttpCase):
    """The preview, image and printout routes answer what the user may read:
    they used to serve any record of any company by its id, under sudo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_rd = cls.env["res.groups"].create({"name": "PLM route R&D"})
        cls.node = cls.env["plm.access"].create(
            {
                "name": "Route R&D",
                "parent_id": cls.env.company.plm_access_id.id,
                "read_group_ids": [Command.set(cls.group_rd.ids)],
            }
        )
        cls.document = cls.env["ir.attachment"].create(
            {
                "name": "ROUTE-1",
                "engineering_code": "ROUTE-1",
                "datas": PIXEL,
                "is_plm": True,
                "preview": PIXEL,
                "plm_access_id": cls.node.id,
            }
        )
        cls.outsider = cls._user("plm_route_outsider")
        cls.insider = cls._user("plm_route_insider", cls.group_rd)

    @classmethod
    def _user(cls, login, extra_group=None):
        groups = cls.env.ref("base.group_user") | cls.env.ref(
            "plm.group_plm_integration_user"
        )
        if extra_group:
            groups |= extra_group
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "password": login,
                "group_ids": [Command.set(groups.ids)],
            }
        )

    def _status(self, login, url):
        self.authenticate(login, login)
        return self.url_open(url).status_code

    def test_the_preview_follows_the_node(self):
        url = "/plm/ir_attachment_preview/%s" % self.document.id
        self.assertEqual(self._status("plm_route_outsider", url), 404)
        self.assertEqual(self._status("plm_route_insider", url), 200)

    def test_the_printout_follows_the_node(self):
        url = "/plm/ir_attachment_printout/%s" % self.document.id
        # No printout on the document, so the answer is "not found" for both:
        # what matters is that the outsider never reaches the rendering.
        self.assertEqual(self._status("plm_route_outsider", url), 404)
        self.assertEqual(self._status("plm_route_insider", url), 404)

    def test_the_product_image_follows_the_access_rights(self):
        product = self.env["product.product"].create(
            {"name": "ROUTE-PROD", "image_1920": PIXEL}
        )
        for url in (
            "/plm/product_product_image_1920/%s" % product.id,
            "/plm/product_product_preview/%s" % product.id,
        ):
            self.assertEqual(self._status("plm_route_insider", url), 200)

    def test_the_download_routes_follow_the_node(self):
        """The CAD client's download: a PLM group was enough, and the search ran
        under sudo, so any document of any company came out by its id."""
        for route in ("/plm/download", "/plm/download_structure"):
            url = "%s?attachment_id=%s&hostname=host&hostpws=pws" % (
                route,
                self.document.id,
            )
            self.assertNotEqual(self._status("plm_route_outsider", url), 200, route)
            self.assertEqual(self._status("plm_route_insider", url), 200, route)

    def test_the_download_routes_need_a_plm_group(self):
        outsider = self.env["res.users"].create(
            {
                "name": "plm_route_no_plm",
                "login": "plm_route_no_plm",
                "password": "plm_route_no_plm",
                "group_ids": [Command.set(self.env.ref("base.group_user").ids)],
            }
        )
        self.assertTrue(outsider)
        url = "/plm/download?attachment_id=%s" % self.document.id
        self.assertEqual(self._status("plm_route_no_plm", url), 403)

    def test_the_upload_routes_take_plm_documents_only(self):
        """They write the file, the preview and the printout by id: an ordinary
        attachment the user may write is not theirs to overwrite."""
        plain = self.env["ir.attachment"].create({"name": "invoice.pdf", "datas": PIXEL})
        self.authenticate("plm_route_insider", "plm_route_insider")
        for route, field in (
            ("/plm_document_upload/upload", "mod_file"),
            ("/plm_document_upload/upload_pdf", "file_stream"),
        ):
            for document, expected in ((plain, 400), (self.document, 200)):
                response = self.url_open(
                    route,
                    data={"doc_id": str(document.id), "filename": "x.sldprt"},
                    files={field: ("x.sldprt", b"x")},
                )
                self.assertEqual(response.status_code, expected, "%s %s" % (route, expected))
        self.assertEqual(plain.datas, PIXEL)

    def test_an_unknown_id_is_not_found(self):
        self.assertEqual(
            self._status("plm_route_insider", "/plm/ir_attachment_preview/999999999"),
            404,
        )
