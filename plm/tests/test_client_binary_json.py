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
import base64
import io
import json

from PIL import Image

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import BinaryBytes
from odoo.tools.json import json_default

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm_client_binary_json")
class TestClientBinaryJson(TransactionCase, PlmEntityCreator):
    """
    The legacy methods the Client2019 calls answer the preview as a base64
    string, as on Odoo 18 and 19, so that the /jsonrpc answer can be built.
    """

    def setUp(self):
        super().setUp()
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64), (30, 30, 200)).save(buffer, format="PNG")
        self.model = self.create_document("binary_json_model.SLDPRT", doc_type="3d")
        self.drawing = self.create_document("binary_json_drawing.SLDDRW", doc_type="2d")
        self.drawing.preview = BinaryBytes(buffer.getvalue())
        self.env["ir.attachment.relation"].create(
            {
                "parent_id": self.model.id,
                "child_id": self.drawing.id,
                "link_kind": "LyTree",
            }
        )

    def _assert_png_base64(self, value):
        self.assertIsInstance(value, str)
        self.assertTrue(base64.b64decode(value).startswith(b"\x89PNG"))

    def _assert_json(self, value):
        json.dumps(value, ensure_ascii=False, default=json_default)

    def test_get_related_docs(self):
        rows = self.model.GetRelatedDocs()
        self.assertEqual([row[0] for row in rows], [self.drawing.id])
        self._assert_png_base64(rows[0][2])
        self._assert_json(rows)

    def test_get_related_docs_without_preview(self):
        rows = self.drawing.GetRelatedDocs()
        self.assertEqual([row[0] for row in rows], [self.model.id])
        self.assertEqual(rows[0][2], "")
        self._assert_json(rows)

    def test_get_document_infos_from_file_name(self):
        infos = self.env["ir.attachment"].GetDocumentInfosFromFileName(
            {"file_name": self.drawing.name}
        )
        self.assertEqual([info["id"] for info in infos], [self.drawing.id])
        self._assert_png_base64(infos[0]["iconStream"])
        self._assert_json(infos)
