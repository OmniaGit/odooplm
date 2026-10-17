##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


class BomFindCase(PlmEntityCreator):
    """
    The standard BoM search made without a type never finds a BoM of a type
    that is not for production (BOM_TYPE), while the lines of such a BoM
    descend into the BoMs of the same type of their components.

    Mix it in a TransactionCase of the module adding BOM_TYPE.
    """

    BOM_TYPE = None
    # the test methods live here, in the mixin: Odoo loads only the ones a
    # TestCase defines itself unless told otherwise
    allow_inherited_tests_method = True

    def setUp(self):
        super().setUp()
        self.product = self.create_product_product("bom_find_product")
        self.normal_component = self.create_product_product("bom_find_normal_comp")
        self.normal_component.standard_price = 1.0
        self.other_component = self.create_product_product("bom_find_other_comp")
        self.other_component.standard_price = 100.0
        # The BoM of BOM_TYPE comes first by sequence: before the fix the
        # standard search took it
        self.other_bom = self._create_bom(
            self.product, self.other_component, self.BOM_TYPE, 10
        )
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

    def test_bom_find_without_type_skips_it(self):
        found = self.env["mrp.bom"]._bom_find(self.product)
        self.assertEqual(found[self.product], self.normal_bom)

    def test_bom_find_with_its_type(self):
        found = self.env["mrp.bom"]._bom_find(self.product, bom_type=self.BOM_TYPE)
        self.assertEqual(found[self.product], self.other_bom)

    def test_bom_find_only_its_type(self):
        product = self.create_product_product("bom_find_only_other")
        self._create_bom(product, self.other_component, self.BOM_TYPE)
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

    def test_child_bom_of_line_of_its_type(self):
        parent = self.create_product_product("bom_find_parent_other")
        parent_bom = self._create_bom(parent, self.product, self.BOM_TYPE)
        self.assertEqual(parent_bom.bom_line_ids.child_bom_id, self.other_bom)
        self.assertEqual(
            parent_bom.bom_line_ids.child_line_ids, self.other_bom.bom_line_ids
        )
