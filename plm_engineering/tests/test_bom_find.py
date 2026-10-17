# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm_bom_find")
class TestBomFindEngineering(TransactionCase, PlmEntityCreator):
    """
    The standard BoM search made without a type never finds an engineering
    BoM, while the lines of an engineering BoM descend into the engineering
    BoMs of their components.
    """

    def setUp(self):
        super().setUp()
        self.product = self.create_product_product("bom_find_product")
        self.normal_component = self.create_product_product("bom_find_normal_comp")
        self.normal_component.standard_price = 1.0
        self.ebom_component = self.create_product_product("bom_find_ebom_comp")
        self.ebom_component.standard_price = 100.0
        # The engineering BoM comes first by sequence: before the fix the
        # standard search took it
        self.ebom = self._create_bom(self.product, self.ebom_component, "ebom", 10)
        self.normal_bom = self._create_bom(
            self.product, self.normal_component, "normal", 20
        )

    def _create_bom(self, product, component, bom_type, sequence=10):
        return self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_id": product.id,
                "type": bom_type,
                "sequence": sequence,
                "bom_line_ids": [
                    (0, 0, {"product_id": component.id, "product_qty": 1})
                ],
            }
        )

    def test_bom_find_without_type_skips_ebom(self):
        found = self.env["mrp.bom"]._bom_find(self.product)
        self.assertEqual(found[self.product], self.normal_bom)

    def test_bom_find_with_type_ebom(self):
        found = self.env["mrp.bom"]._bom_find(self.product, bom_type="ebom")
        self.assertEqual(found[self.product], self.ebom)

    def test_bom_find_only_ebom(self):
        product = self.create_product_product("bom_find_only_ebom")
        self._create_bom(product, self.ebom_component, "ebom")
        found = self.env["mrp.bom"]._bom_find(product)
        self.assertFalse(found[product])

    def test_price_from_bom_uses_normal_bom(self):
        if not hasattr(self.product, "button_bom_cost"):
            self.skipTest("mrp_account is not installed")
        self.product.button_bom_cost()
        self.assertEqual(self.product.standard_price, 1.0)

    def test_child_bom_of_normal_line(self):
        parent = self.create_product_product("bom_find_parent_normal")
        parent_bom = self._create_bom(parent, self.product, "normal")
        self.assertEqual(parent_bom.bom_line_ids.child_bom_id, self.normal_bom)

    def test_child_bom_of_ebom_line(self):
        parent = self.create_product_product("bom_find_parent_ebom")
        parent_bom = self._create_bom(parent, self.product, "ebom")
        self.assertEqual(parent_bom.bom_line_ids.child_bom_id, self.ebom)
        self.assertEqual(
            parent_bom.bom_line_ids.child_line_ids, self.ebom.bom_line_ids
        )
