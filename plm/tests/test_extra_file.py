##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_extra_file
#


@tagged("-standard", "odoo_plm", "odoo_plm_extra_file")
class PlmExtraFile(TransactionCase, PlmEntityCreator):

    def _extra_relations(self, parent, child):
        return self.env["ir.attachment.relation"].search(
            [
                ("parent_id", "=", parent.id),
                ("child_id", "=", child.id),
                ("link_kind", "=", "ExtraTree"),
            ]
        )

    def test_create_linked_to_source_and_product(self):
        """A new extra file becomes a PLM document, child of its source by an
        ExtraTree relation, linked to the first product of the source."""
        product, source = self.create_product_document("extra_create", "2d")
        extra = self.env["ir.attachment"]._save_extra_file(
            b"dwg content",
            "extra_create_dwg",
            file_name="extra_create_dwg.dwg",
            related_attachment_id=source.id,
        )
        self.assertEqual(len(extra), 1)
        self.assertTrue(extra.is_plm)
        self.assertEqual(extra.name, "extra_create_dwg.dwg")
        self.assertEqual(extra.engineering_code, "extra_create_dwg")
        self.assertEqual(extra.engineering_revision, 0)
        self.assertEqual(extra.raw, b"dwg content")
        self.assertEqual(len(self._extra_relations(source, extra)), 1)
        self.assertIn(product, extra.linkedcomponents)

    def test_update_found_by_code(self):
        """An extra file with the code of an existing document replaces its
        file: no second document, no second relation, no backup."""
        _product, source = self.create_product_document("extra_update", "2d")
        first = self.env["ir.attachment"]._save_extra_file(
            b"old", "extra_update_dwg", related_attachment_id=source.id
        )
        backups = self.env["plm.backupdoc"].search_count(
            [("documentid", "=", first.id)]
        )
        second = self.env["ir.attachment"]._save_extra_file(
            b"new", "extra_update_dwg", related_attachment_id=source.id
        )
        self.assertEqual(second, first)
        self.assertEqual(first.raw, b"new")
        self.assertEqual(first.name, "extra_update_dwg")
        self.assertEqual(len(self._extra_relations(source, first)), 1)
        self.assertEqual(
            self.env["plm.backupdoc"].search_count([("documentid", "=", first.id)]),
            backups,
        )

    def test_explicit_product(self):
        """The product given is linked instead of the one of the source."""
        _product, source = self.create_product_document("extra_product", "3d")
        other = self.create_product_product("extra_other_product")
        extra = self.env["ir.attachment"]._save_extra_file(
            b"step",
            "extra_product_step",
            related_attachment_id=source.id,
            product_id=other.id,
        )
        self.assertEqual(extra.linkedcomponents, other)

    def test_without_source(self):
        """Without a source document no relation is created."""
        extra = self.env["ir.attachment"]._save_extra_file(b"alone", "extra_alone")
        self.assertFalse(
            self.env["ir.attachment.relation"].search_count(
                [("child_id", "=", extra.id)]
            )
        )


# at install: the post install run pregenerates the assets first
@tagged(
    "-standard", "odoo_plm", "odoo_plm_extra_file", "at_install", "-post_install"
)
class PlmExtraFileHttp(HttpCase, PlmEntityCreator):

    def test_route_uses_shared_method(self):
        """/plm_document_upload/extra_file creates the document as before."""
        _product, source = self.create_product_document("extra_http", "2d")
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/plm_document_upload/extra_file",
            data={
                "doc_name": "extra_http_dwg",
                "doc_rev": "0",
                "related_attachment_id": str(source.id),
                "product_id": "",
                "filename": "extra_http_dwg.dwg",
            },
            files={"file_stream": ("extra_http_dwg.dwg", b"http content")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        extra = self.env["ir.attachment"].search(
            [("engineering_code", "=", "extra_http_dwg")]
        )
        self.assertEqual(len(extra), 1)
        self.assertEqual(base64.b64decode(extra.datas), b"http content")
        self.assertEqual(extra.name, "extra_http_dwg.dwg")
        self.assertEqual(source.linkedcomponents, extra.linkedcomponents)

    def test_route_without_name(self):
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/plm_document_upload/extra_file",
            data={"doc_name": ""},
            files={"file_stream": ("x.dwg", b"x")},
        )
        self.assertEqual(response.status_code, 400, response.text)
