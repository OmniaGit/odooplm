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


@tagged("-standard", "odoo_plm_bom_overview")
class TestBomOverviewImage(TransactionCase, PlmEntityCreator):
    """
    The BoM overview carries the product images as base64 strings, so that its
    json answer can be built (a binary field value cannot go in it as is).
    """

    def _png(self):
        buffer = io.BytesIO()
        Image.new("RGB", (300, 300), (200, 30, 30)).save(buffer, format="PNG")
        return BinaryBytes(buffer.getvalue())

    def setUp(self):
        super().setUp()
        self.parent = self.create_product_product("bom_overview_parent")
        self.child = self.create_product_product("bom_overview_child")
        self.bare = self.create_product_product("bom_overview_bare")
        self.parent.image_1920 = self._png()
        self.child.image_1920 = self._png()
        self.bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.parent.product_tmpl_id.id,
                "product_id": self.parent.id,
                "bom_line_ids": [
                    (0, 0, {"product_id": self.child.id, "product_qty": 1}),
                    (0, 0, {"product_id": self.bare.id, "product_qty": 1}),
                ],
            }
        )

    def _overview(self):
        return self.env["report.mrp.report_bom_structure"].get_html(
            bom_id=self.bom.id
        )

    def _assert_png_base64(self, value):
        self.assertIsInstance(value, str)
        self.assertTrue(base64.b64decode(value).startswith(b"\x89PNG"))

    def test_images_are_base64_strings(self):
        lines = self._overview()["lines"]
        self._assert_png_base64(lines["image_component"])
        components = {c["product_id"]: c for c in lines["components"]}
        self._assert_png_base64(components[self.child.id]["image_component"])
        self.assertFalse(components[self.bare.id]["image_component"])

    def test_the_answer_goes_in_json(self):
        json.dumps(self._overview(), ensure_ascii=False, default=json_default)
