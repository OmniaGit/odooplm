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
import io

from PIL import Image

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_component_preview
#


def _png(color):
    """A base64 string, as the upload controller writes it: on 20 a binary
    field refuses plain bytes."""
    stream = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode()


@tagged("-standard", "odoo_plm_component_preview")
class PlmComponentPreview(TransactionCase, PlmEntityCreator):
    """The image of a product comes from the preview of its 3D model, or of
    its 2D drawing when it has no 3D document (a DWG saved from AutoCAD)."""

    def _document(self, name, doc_type, color, product):
        document = self.create_document(name, doc_type=doc_type)
        document.write({"is_plm": True, "preview": _png(color)})
        product.linkeddocuments = [(4, document.id)]
        return document

    def test_2d_only_gives_the_image(self):
        product = self.create_product_product("preview_dwg_only")
        drawing = self._document("preview_dwg_only.dwg", "2d", "red", product)
        drawing.update_component_preview()
        self.assertTrue(product.image_1920)
        self.assertEqual(product.image_1920.content, drawing.preview.content)

    def test_3d_wins_over_2d(self):
        product = self.create_product_product("preview_both")
        model = self._document("preview_both.sldprt", "3d", "blue", product)
        drawing = self._document("preview_both.slddrw", "2d", "red", product)
        model.update_component_preview()
        drawing.update_component_preview()
        self.assertEqual(product.image_1920.content, model.preview.content)

    def test_3d_without_preview_still_blocks_2d(self):
        product = self.create_product_product("preview_model_no_preview")
        model = self.create_document("preview_model_no_preview.ipt", doc_type="3d")
        product.linkeddocuments = [(4, model.id)]
        drawing = self._document("preview_model_no_preview.dwg", "2d", "red", product)
        drawing.update_component_preview()
        self.assertFalse(product.image_1920)

    def test_3d_gives_the_image(self):
        product = self.create_product_product("preview_3d")
        model = self._document("preview_3d.ipt", "3d", "blue", product)
        model.update_component_preview()
        self.assertEqual(product.image_1920.content, model.preview.content)

    def test_other_document_gives_nothing(self):
        product = self.create_product_product("preview_other")
        other = self._document("preview_other.pdf", "other", "green", product)
        other.update_component_preview()
        self.assertFalse(product.image_1920)

    def test_cron_follows_the_same_rule(self):
        only_2d = self.create_product_product("cron_dwg_only")
        drawing = self._document("cron_dwg_only.dwg", "2d", "red", only_2d)
        both = self.create_product_product("cron_both")
        model = self._document("cron_both.ipt", "3d", "blue", both)
        self._document("cron_both.dwg", "2d", "red", both)
        self.env["ir.config_parameter"].sudo().set_str(
            "LAST_DT_PREVIEW_UPDATE", "False"
        )
        self.env["ir.attachment"].updatePreviews()
        self.assertEqual(only_2d.image_1920.content, drawing.preview.content)
        self.assertEqual(both.image_1920.content, model.preview.content)
