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


@tagged("-standard", "odoo_plm_client_related_documents")
class TestClientRelatedDocuments(TransactionCase, PlmEntityCreator):
    """
    plm.client.get_related_documents, the CoreBom client's Open related
    documents in one call: the previews only when there is a choice to make.
    """

    def setUp(self):
        super().setUp()
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64), (30, 200, 30)).save(buffer, format="PNG")
        self.png = BinaryBytes(buffer.getvalue())
        self.model = self.create_document("related_docs_model.SLDPRT", doc_type="3d")
        self.drawing = self.create_document("related_docs_a.SLDDRW", doc_type="2d")
        self.drawing.preview = self.png
        self._relate(self.model, self.drawing)
        self.client = self.env["plm.client"]

    def _relate(self, model, drawing):
        self.env["ir.attachment.relation"].create(
            {"parent_id": model.id, "child_id": drawing.id, "link_kind": "LyTree"}
        )

    def _props(self, document):
        return {
            "engineering_code": document.engineering_code,
            "engineering_revision": document.engineering_revision,
        }

    def _call(self, document_props):
        answer = self.client.get_related_documents(document_props)
        json.dumps(answer, ensure_ascii=False, default=json_default)
        return answer

    def test_unknown_document(self):
        answer = self._call({"engineering_code": "no_such_code", "engineering_revision": 0})
        self.assertEqual(answer, {"document_id": False, "related": []})
        self.assertEqual(self._call({}), {"document_id": False, "related": []})

    def test_one_related_document_comes_without_preview(self):
        answer = self._call(self._props(self.model))
        self.assertEqual(answer["document_id"], self.model.id)
        self.assertEqual(len(answer["related"]), 1)
        row = answer["related"][0]
        self.assertEqual(row["id"], self.drawing.id)
        self.assertEqual(row["engineering_code"], self.drawing.engineering_code)
        self.assertEqual(row["engineering_revision"], self.drawing.engineering_revision)
        self.assertEqual(row["document_type"], "2d")
        self.assertEqual(row["preview"], "")

    def test_several_related_documents_come_with_previews(self):
        other = self.create_document("related_docs_b.SLDDRW", doc_type="2d")
        self._relate(self.model, other)
        answer = self._call(self._props(self.model))
        rows = {row["id"]: row for row in answer["related"]}
        self.assertEqual(set(rows), {self.drawing.id, other.id})
        self.assertTrue(
            base64.b64decode(rows[self.drawing.id]["preview"]).startswith(b"\x89PNG")
        )
        self.assertEqual(rows[other.id]["preview"], "")

    def test_same_documents_as_get_related_docs(self):
        answer = self._call(self._props(self.drawing))
        self.assertEqual(
            [row["id"] for row in answer["related"]],
            [row[0] for row in self.drawing.GetRelatedDocs()],
        )
