##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
Created on 8 Oct 2021

@author: mboscolo
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
#
# --test-tags=odoo_plm
#
#
DUMMY_CONTENT = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


#
@tagged("-standard", "odoo_plm_web_revision")
class PlmDateBom(TransactionCase, PlmEntityCreator):

    def test_product_attachment_wk(self):
        product, document = self.create_product_document("test_product_attachment_wk")
        product.action_confirm()
        product.action_release()
        #
        wiz_obj = self.env["product.rev_wizard"].create({"reviseDocument": True})
        wiz_obj.with_context(
            active_id=product.id, active_model="product.product"
        ).action_create_new_revision_by_server()
        #
        assert product.product_tmpl_id.get_latest_version().engineering_revision == 1
        assert document.get_latest_version().engineering_revision == 1

    def test_bom_wk(self):
        new_bom = self.create_bom_with_document("test_bom_wk")
        product = new_bom.product_id
        product.action_confirm()
        product.action_release()
        wiz_obj = self.env["product.rev_wizard"].create(
            {"reviseDocument": True, "reviseNbom": True}
        )
        wiz_obj.with_context(
            active_id=product.id, active_model="product.product"
        ).action_create_new_revision_by_server()
