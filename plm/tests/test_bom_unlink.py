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
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_bom_unlink
#


@tagged("-standard", "odoo_plm_bom_unlink")
class PlmBomUnlink(TransactionCase, PlmEntityCreator):
    """A BoM of a component with an engineering code is deleted only while
    the component is a draft (issue #123: the refusal raised NameError)."""

    def _bom_of(self, name):
        product = self.create_product_product(name)
        bom = self.env["mrp.bom"].create(
            {"product_id": product.id, "product_tmpl_id": product.product_tmpl_id.id}
        )
        return product, bom

    def test_bom_of_released_component_is_refused(self):
        product, bom = self._bom_of("bom_unlink_released")
        product.action_confirm()
        product.action_release()
        self.assertEqual(product.engineering_state, "released")
        with self.assertRaises(UserError) as error:
            bom.unlink()
        message = str(error.exception)
        self.assertIn(product.product_tmpl_id.display_name, message)
        self.assertIn(bom.display_name, message)
        self.assertIn("Released", message)
        self.assertTrue(bom.exists())

    def test_bom_of_draft_component_is_deleted(self):
        product, bom = self._bom_of("bom_unlink_draft")
        self.assertEqual(product.engineering_state, "draft")
        bom.unlink()
        self.assertFalse(bom.exists())
