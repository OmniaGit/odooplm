# -*- coding: utf-8 -*-
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
'''
Created on 8 Oct 2021

@author: mboscolo
'''
import logging
import datetime
from odoo import models
from odoo import Command
from odoo import fields
from odoo import api
from odoo import _
from odoo.tests import tagged
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests.common import TransactionCase
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUS
from odoo.addons.plm.models.plm_mixin import UNDER_MODIFY_STATUS
from odoo.addons.plm.models.plm_mixin import START_STATUS
from odoo.addons.plm.models.plm_mixin import CONFIRMED_STATUS
from odoo.addons.plm.models.plm_mixin import OBSOLATED_STATUS
#
#
# --test-tags=odoo_plm
#
#
DUMMY_CONTENT = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
#
@tagged('-standard', 'odoo_plm')
class PlmDateBom(TransactionCase):
    def test_some_wk(cls):
        #
        # Product environment related data
        #
        product_product_name = "plm_test_product_product_name_wf"
        product_product_code = "plm_test_product_product_code_wf"
        Uom = cls.env['uom.uom']
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.uom_dunit = Uom.create({
            'name': 'DeciUnit',
            'category_id': cls.uom_unit.category_id.id,
            'factor_inv': 0.1,
            'factor': 10.0,
            'uom_type': 'smaller',
            'rounding': 0.001})
        cls.uom_weight = cls.env.ref('uom.product_uom_kgm')
        #
        # create main product
        #
        Product = cls.env['product.product'] 
        default_data = Product.default_get([])
        default_data.update({
            'name': product_product_name,
            'engineering_code' : product_product_code,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'sale_line_warn':'no-message'})
        cls.product_parent_id = Product.create(default_data)
     
        #
        # release the product
        #
        cls.product_parent_id.action_confirm()
        cls.product_parent_id.action_release()
        assert cls.product_parent_id.engineering_state==RELEASED_STATUS
        assert cls.product_parent_id.product_tmpl_id.get_latest_version().engineering_revision==0
        assert cls.product_parent_id.product_tmpl_id.get_previus_version().engineering_revision==0
        assert cls.product_parent_id.product_tmpl_id.get_next_version().engineering_revision==0
        assert cls.product_parent_id.product_tmpl_id.get_released().engineering_revision==0
        assert cls.product_parent_id.product_tmpl_id.get_released().engineering_code==product_product_code
        assert len(cls.product_parent_id.product_tmpl_id.get_all_revision())==1
        assert cls.product_parent_id.product_tmpl_id.is_released()==True
        assert cls.product_parent_id.product_tmpl_id.engineering_revision_count==1
        #
        # work on copy
        #
        product_product_copy = cls.product_parent_id.product_tmpl_id.copy({'name': 'product_product_copy'})
        assert product_product_copy.engineering_code in ['','-', False]
        assert product_product_copy.engineering_revision==0
        assert product_product_copy.name=='product_product_copy'
        #
        # make new revision
        #
        cls.product_parent_id.product_tmpl_id.new_version()
        #
        assert cls.product_parent_id.product_tmpl_id.get_previus_version() == cls.env['product.template']     
        #
        latest_version = cls.product_parent_id.product_tmpl_id.get_latest_version()
        assert latest_version.engineering_revision==1
        assert latest_version.engineering_state==START_STATUS
        assert latest_version.engineering_code==product_product_code
        #
        prev_version = latest_version.get_previus_version()
        assert prev_version.engineering_revision==0
        assert prev_version.engineering_state==UNDER_MODIFY_STATUS
        assert prev_version.engineering_code==product_product_code
        #
        next_version = cls.product_parent_id.product_tmpl_id.get_next_version()
        assert next_version.engineering_revision==1
        assert next_version.engineering_state==START_STATUS
        assert next_version.engineering_code==product_product_code
        assert next_version.is_released()==False         
        #
        released_version = cls.product_parent_id.product_tmpl_id.get_released()
        assert released_version.engineering_revision==0
        assert released_version.engineering_state==UNDER_MODIFY_STATUS
        assert released_version.engineering_code==product_product_code        
        assert released_version.is_released()==True
        #
        assert len(cls.product_parent_id.product_tmpl_id.get_all_revision())==2
        assert cls.product_parent_id.product_tmpl_id.is_released()==True
        assert cls.product_parent_id.product_tmpl_id.engineering_revision_count==1
        #
        #
        #
        latest_version = cls.product_parent_id.product_tmpl_id.get_latest_version()
        latest_version.action_from_draft_to_confirmed()
        latest_version.action_from_confirmed_to_release()
        #
        assert latest_version.engineering_revision==1
        assert latest_version.engineering_code==product_product_code
        assert latest_version.is_released()==True
        #
        prev_version = latest_version.get_previus_version()
        assert prev_version.engineering_state==OBSOLATED_STATUS
        #
        latest_version.new_version()
        for revision in latest_version.get_all_revision():
            if revision.engineering_revision==0:
                assert revision.engineering_state==OBSOLATED_STATUS
            elif revision.engineering_revision==1:
                assert revision.engineering_state==UNDER_MODIFY_STATUS
            elif revision.engineering_revision==2:
                assert revision.engineering_state==START_STATUS
        #
        # template
        #
        ProductTemplate = cls.env['product.template']
        default_data = ProductTemplate.default_get([])
        default_data.update({
            'name': 'test_product_template',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})                                  
        cls.product_tmpl_1 = Product.create(default_data)
        cls.product_tmpl_copy = cls.product_tmpl_1.copy({'name': 'test_product_template_copy'})         
        
    def test_attachment_wk(self):
        attachment = self.env['ir.attachment'].create({
            'datas': DUMMY_CONTENT,
            'name': 'DUMMY_CONTENT.gif',
            'engineering_code': 'test_ir_attachment',
            'res_model': 'documents.document',
            'res_id': 0,
        })
        #
        assert attachment.engineering_code==0
        assert attachment.ischecked_in()==False
        #
        attchment.check.toggle_check_out()
        assert attachment.ischecked_in()==True
        attchment.check.toggle_check_out()      
        assert attachment.ischecked_in()==False
        #
        attchment.action_confirm()
        attchment.engineering_state==CONFIRMED_STATUS
        attchment.action_reactivate()
        attchment.engineering_state==START_STATUS
        attchment.action_confirm()
        attchment.action_release()
        assert latest_version.is_released()==True
        #
        #  new version
        #
        #attachment.
    