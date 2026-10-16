# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Created on 16 Oct 2026

@author: mboscolo
"""
import base64

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase

#
# --test-tags=odoo_plm_document_code
#

FILE_CONTENT = base64.b64encode(b"cad file").decode()


@tagged("-standard", "odoo_plm_document_code")
class PlmDocumentCode(TransactionCase):
    """A document created in the PLM form needs its engineering code, and a
    file uploaded there gives it one when it is empty."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plm_admin = cls.env["res.users"].create(
            {
                "name": "PLM document code admin",
                "login": "plm_document_code_admin",
                "group_ids": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("plm.group_plm_admin").id),
                ],
            }
        )
        cls.Attachment = cls.env["ir.attachment"].with_user(cls.plm_admin)

    def _plm_form(self, context=None):
        return Form(
            self.Attachment.with_context(context or {"odooPLM": True}),
            view="plm.view_attachment_form_plm_hinerit",
        )

    def test_upload_fills_the_code(self):
        form = self._plm_form()
        form.name = "PRT-DOC-001.SLDPRT"
        form.raw = FILE_CONTENT
        self.assertEqual(form.engineering_code, "PRT-DOC-001")
        document = form.save()
        self.assertEqual(document.engineering_code, "PRT-DOC-001")
        self.assertTrue(document.is_plm)

    def test_file_name_without_extension(self):
        form = self._plm_form()
        form.name = "PRT-DOC-002"
        form.raw = FILE_CONTENT
        self.assertEqual(form.engineering_code, "PRT-DOC-002")

    def test_a_written_code_is_kept(self):
        form = self._plm_form()
        form.engineering_code = "MY-CODE"
        form.name = "PRT-DOC-003.SLDPRT"
        form.raw = FILE_CONTENT
        self.assertEqual(form.engineering_code, "MY-CODE")

    def test_no_code_no_save(self):
        form = self._plm_form()
        form.name = "no code"
        with self.assertRaisesRegex(AssertionError, "engineering_code"):
            form.save()

    def test_outside_plm_no_code(self):
        attachment = self.Attachment.new(
            {"name": "invoice.pdf", "raw": b"pdf file"}
        )
        attachment._onchange_raw_engineering_code()
        self.assertFalse(attachment.engineering_code)
