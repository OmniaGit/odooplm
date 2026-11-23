# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
import zipfile
from io import BytesIO

from odoo.tests import tagged
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
#
# --test-tags=odoo_pack_and_go
#
#


@tagged("-standard", "odoo_pack_and_go")
class PackAndGoImport(TransactionCase, PlmEntityCreator):
    def _prepare_pack_and_go(self, name):
        product, _bom = self.get_3_level_assembly(name)
        pack_and_go_id = self.env["pack.and_go"].create(
            {"component_id": product.product_tmpl_id.id}
        )
        pack_and_go_id.export_type_id = self.env.ref(
            "plm_pack_and_go.pack_go_export_type_all"
        )
        pack_and_go_id.bom_computation = "ALL_LEVEL"
        pack_and_go_id.action_compute_attachment_bom()
        rows = (
            pack_and_go_id.export_2d
            + pack_and_go_id.export_3d
            + pack_and_go_id.export_pdf
            + pack_and_go_id.export_other
        )
        return pack_and_go_id, rows.document_id

    def _import(self, zip_datas):
        wizard = self.env["pack.and.go.import"].create({"zip_file": zip_datas})
        wizard.action_import()
        return wizard

    def _edit_zip_entry(self, zip_datas, entry_name, new_content):
        """A copy of the zip with entry_name's content replaced, everything
        else (notably exported_data.json) unchanged."""
        original = zipfile.ZipFile(BytesIO(bytes(zip_datas)))
        out = BytesIO()
        with zipfile.ZipFile(out, "w") as rebuilt:
            for name in original.namelist():
                content = new_content if name == entry_name else original.read(name)
                rebuilt.writestr(name, content)
        return base64.b64encode(out.getvalue()).decode()

    def test_import_replaces_content_and_checks_in(self):
        pack_and_go_id, document_ids = self._prepare_pack_and_go(
            "pack_and_go_import_ok"
        )
        self.assertTrue(document_ids, "expected at least one document to export")
        pack_and_go_id.action_create_zip_checkout()
        self.assertTrue(
            self.env["plm.checkout"].search([("documentid", "in", document_ids.ids)]),
            "the export should have checked the documents out",
        )

        edited_document = document_ids[0]
        new_content = b"EDITED CONTENT FOR TEST"
        edited_zip = self._edit_zip_entry(
            pack_and_go_id.datas, edited_document.name, new_content
        )

        wizard = self._import(edited_zip)
        self.assertEqual(wizard.state, "done")
        self.assertEqual(
            len(wizard.document_ids), len(document_ids), "every document imported"
        )
        self.assertEqual(bytes(edited_document.raw), new_content)
        self.assertFalse(
            self.env["plm.checkout"].search([("documentid", "in", document_ids.ids)]),
            "every document should be checked back in",
        )

    def test_preview_shows_changed_and_unchanged(self):
        pack_and_go_id, document_ids = self._prepare_pack_and_go(
            "pack_and_go_import_preview"
        )
        self.assertGreater(
            len(document_ids), 1, "need more than one document to tell changed from unchanged"
        )
        pack_and_go_id.action_create_zip_checkout()

        edited_document = document_ids[0]
        unchanged_document = document_ids[1]
        edited_zip = self._edit_zip_entry(
            pack_and_go_id.datas, edited_document.name, b"EDITED CONTENT FOR TEST"
        )

        wizard = self.env["pack.and.go.import"].create({"zip_file": edited_zip})
        wizard.action_load_preview()
        self.assertEqual(wizard.state, "preview")

        lines_by_document = {line.document_id: line for line in wizard.line_ids}
        self.assertEqual(lines_by_document[edited_document].status, "changed")
        self.assertEqual(lines_by_document[unchanged_document].status, "unchanged")
        # Loading the preview must not touch anything yet
        self.assertTrue(
            self.env["plm.checkout"].search([("documentid", "in", document_ids.ids)]),
            "nothing should be checked in before Import is actually clicked",
        )

        wizard.action_import()
        self.assertEqual(wizard.state, "done")
        self.assertEqual(bytes(edited_document.raw), b"EDITED CONTENT FOR TEST")

    def test_import_skips_documents_not_checked_out(self):
        """A plain "Download zip" (no checkout) holds no manifest: nothing to
        import. A zip built with checkout, but checked back in by hand
        before the import runs, is reported and left untouched."""
        pack_and_go_id, document_ids = self._prepare_pack_and_go(
            "pack_and_go_import_not_checked_out"
        )
        pack_and_go_id.action_create_zip_checkout()
        self.env["plm.checkout"].search(
            [("documentid", "in", document_ids.ids)]
        ).unlink()

        wizard = self._import(pack_and_go_id.datas)
        self.assertEqual(wizard.state, "done")
        self.assertFalse(wizard.document_ids, "nothing should have been imported")
        self.assertIn("not checked out by you", wizard.result)

    def test_import_rejects_a_zip_without_manifest(self):
        plain_zip = BytesIO()
        with zipfile.ZipFile(plain_zip, "w") as zip_file:
            zip_file.writestr("not_a_manifest.txt", b"nothing to see here")
        wizard = self.env["pack.and.go.import"].create(
            {"zip_file": base64.b64encode(plain_zip.getvalue()).decode()}
        )
        with self.assertRaises(UserError):
            wizard.action_import()
