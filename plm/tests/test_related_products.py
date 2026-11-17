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
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_related_products
#


@tagged("-standard", "odoo_plm_related_products")
class PlmRelatedProducts(TransactionCase, PlmEntityCreator):
    """related_products of the download structure carries one row per
    product linked to the document (it used to be {product_id: None}, so the
    client could not open a document in the configuration of its product)."""

    def test_related_products_rows(self):
        product = self.create_product_product("related_products")
        product.configuration_name = "CFG-A"
        document = self.create_document("related_products.sldprt")
        product.linkeddocuments = [(4, document.id)]

        related = document.get_download_dict("host", "pws")["related_products"]

        template = product.product_tmpl_id
        self.assertEqual(
            related,
            {
                product.id: {
                    "ent_id": template.id,
                    "engineering_code": template.engineering_code,
                    "engineering_revision": template.engineering_revision,
                    "configuration_name": "CFG-A",
                    "name": template.name,
                }
            },
        )

    def test_document_without_products(self):
        document = self.create_document("no_products.sldprt")
        self.assertEqual(
            document.get_download_dict("host", "pws")["related_products"], {}
        )
