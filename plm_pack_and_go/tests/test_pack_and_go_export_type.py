# -*- coding: utf-8 -*-
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
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Export types of the Pack and Go: the tab each document goes to, the
extension filter, and the stamped print of the PDF tab.

--test-tags=odoo_pack_and_go_export_type
"""
import base64
import os
import tempfile
from io import BytesIO

from reportlab.pdfgen import canvas

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.pdf import PdfFileReader
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


def _pdf_bytes(text):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(100, 700, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@tagged("-standard", "odoo_pack_and_go_export_type")
class TestPackAndGoExportType(TransactionCase, PlmEntityCreator):

    def setUp(self):
        super().setUp()
        self.product = self.create_product_product("pack_go_export_type")
        self.doc_2d = self.create_document("drawing.dwg", doc_type="2d")
        self.doc_3d = self.create_document("model.step", doc_type="3d")
        self.doc_3d_native = self.create_document("model.sldprt", doc_type="3d")
        self.doc_pdf = self.create_document("datasheet.pdf")
        self.doc_pdf.raw = _pdf_bytes("datasheet")
        self.doc_txt = self.create_document("notes.txt")
        self.doc_no_type = self.create_document("presentation.pptx", doc_type="pr")
        for document in (
            self.doc_2d,
            self.doc_3d,
            self.doc_3d_native,
            self.doc_pdf,
            self.doc_txt,
            self.doc_no_type,
        ):
            document.linkedcomponents = [(4, self.product.id)]
        self.export_all = self.env.ref("plm_pack_and_go.pack_go_export_type_all")

    def _compute(self, export_type):
        wizard = self.env["pack.and_go"].create(
            {
                "component_id": self.product.product_tmpl_id.id,
                "export_type_id": export_type.id,
                "bom_computation": "ONLY_PRODUCT",
            }
        )
        wizard.action_compute_attachment_bom()
        return wizard

    def _documents(self, rows):
        return set(rows.mapped("document_id.name"))

    def test_default_export_type(self):
        wizard = self.env["pack.and_go"].create(
            {"component_id": self.product.product_tmpl_id.id}
        )
        self.assertEqual(wizard.export_type_id, self.export_all)

    def test_extension_is_normalized(self):
        extension = self.env["plm.pack.go.extension"].create({"name": " STEP "})
        self.assertEqual(extension.name, ".step")
        extension.name = "Dxf"
        self.assertEqual(extension.name, ".dxf")

    def test_tabs_by_document_type(self):
        wizard = self._compute(self.export_all)
        self.assertEqual(self._documents(wizard.export_2d), {"drawing.dwg"})
        self.assertEqual(
            self._documents(wizard.export_3d), {"model.step", "model.sldprt"}
        )
        # The printout of the drawing and the PDF file
        self.assertEqual(
            self._documents(wizard.export_pdf), {"drawing.dwg", "datasheet.pdf"}
        )
        # Neither 2D, 3D nor PDF: other, and also a type that is none of them
        self.assertEqual(
            self._documents(wizard.export_other), {"notes.txt", "presentation.pptx"}
        )

    def test_flags_select_the_tabs(self):
        export_type = self.env["plm.pack.go.export.type"].create(
            {"name": "3D only", "include_3d": True}
        )
        wizard = self._compute(export_type)
        self.assertEqual(
            self._documents(wizard.export_3d), {"model.step", "model.sldprt"}
        )
        self.assertFalse(wizard.export_2d)
        self.assertFalse(wizard.export_pdf)
        self.assertFalse(wizard.export_other)

    def test_extension_filter(self):
        export_type = self.env["plm.pack.go.export.type"].create(
            {
                "name": "Neutral formats",
                "include_2d": True,
                "include_pdf": True,
                "include_3d": True,
                "include_other": True,
                "extension_ids": [
                    (0, 0, {"name": "step"}),
                    (0, 0, {"name": ".TXT"}),
                ],
            }
        )
        wizard = self._compute(export_type)
        self.assertEqual(self._documents(wizard.export_3d), {"model.step"})
        self.assertEqual(self._documents(wizard.export_other), {"notes.txt"})
        self.assertFalse(wizard.export_2d)
        # The printout is not a file of its own: the filter leaves it alone,
        # while the PDF file is filtered out.
        self.assertEqual(self._documents(wizard.export_pdf), {"drawing.dwg"})

    def test_pdf_tab_is_printed_with_the_stamp(self):
        self.doc_2d.printout = base64.b64encode(_pdf_bytes("drawing")).decode()
        wizard = self._compute(self.export_all)
        with tempfile.TemporaryDirectory() as out_dir:
            wizard.exportPdf(out_dir)
            self.assertEqual(
                sorted(os.listdir(out_dir)), ["datasheet.pdf", "drawing.dwg.pdf"]
            )
            for file_name in os.listdir(out_dir):
                with open(os.path.join(out_dir, file_name), "rb") as pdf_file:
                    text = PdfFileReader(pdf_file).getPage(0).extractText()
                self.assertIn(f"Printed by '{self.env.user.name}'", text, file_name)
                self.assertIn("State: draft", text, file_name)
