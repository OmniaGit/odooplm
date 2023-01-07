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
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator
#
#
# --test-tags=odoo_plm
#
#

#
@tagged('-standard', 'odoo_plm','post_install', '-at_install')
class PlmDateBom(TransactionCase, PlmEntityCreator):
        
    def test_1_some_wk(cls):
        #
        # Product environment related data
        #
        product_product_name = "plm_test_product_product_name_wf"
        product_product_code = "plm_test_product_product_code_wf"
        #
        # create main product
        #
        cls.product_parent_id=cls.create_product_product(product_product_name,product_product_code)
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
        parent_revision = cls.product_parent_id.product_tmpl_id
        assert len(parent_revision.get_all_revision())==2
        assert parent_revision.is_released()==True
        assert parent_revision.engineering_revision_count==2
        #
        #
        #
        latest_version = cls.product_parent_id.product_tmpl_id.get_latest_version()
        latest_version.action_from_draft_to_confirmed()
        latest_version.action_from_confirmed_to_released()
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
        cls.product_tmpl_1 = cls.create_product_template('test_product_template')
        cls.product_tmpl_copy = cls.product_tmpl_1.copy({'name': 'test_product_template_copy'})         
        
    def test_2_attachment_wk(self):
        attachment = self.create_document('document_wk_test')
        #
        assert attachment.engineering_revision==0
        assert attachment.ischecked_in()==True
        #
        attachment.toggle_check_out()
        assert attachment.ischecked_in()==False
        attachment.toggle_check_out()      
        assert attachment.ischecked_in()==True
        #
        attachment.action_confirm()
        attachment.engineering_state==CONFIRMED_STATUS
        attachment.action_reactivate()
        attachment.engineering_state==START_STATUS
        attachment.action_confirm()
        attachment.action_release()
        latest_version = attachment.get_latest_version()
        assert latest_version.is_released()==True
        #
        #  new version
        #
        attachment.new_version()
        assert attachment.engineering_state==UNDER_MODIFY_STATUS
        #
        new_version_attachment = attachment.get_next_version()
        #
        assert new_version_attachment.engineering_revision==1
        assert new_version_attachment.engineering_state==START_STATUS
        #
    
    def test_3_product_attachment_wk(self):
        product = self.create_product_product("test_product_attachment_product")
        document = self.create_document("test_product_attachment_docuemnt")
        document.linkedcomponents =[(4,product.product_tmpl_id.id)]
        #
        # test confirm
        #
        product.action_confirm()
        assert product.engineering_state==CONFIRMED_STATUS
        assert document.engineering_state==CONFIRMED_STATUS
        #
        # test confirm->draft
        #
        product.action_draft()
        assert product.engineering_state==START_STATUS
        assert document.engineering_state==START_STATUS , "status is %s" % document.engineering_state
        #
        # test release
        #
        product.action_confirm()
        product.action_release()
        assert product.engineering_state==RELEASED_STATUS, "status is %s" % product.engineering_state
        assert document.engineering_state==RELEASED_STATUS, "status is %s" % document.engineering_state
    
    def test_4_bom_wk(self):
        bom_id = self.create_bom_with_document("base_test_bom_wk")
        root_product_id = bom_id.product_id
        root_product_id.action_confirm()
        
        children_ids =  self.env['product.product']._getChildrenBom(root_product_id,
                                                                    level=1)
        for child in self.env['product.product'].browse(children_ids):
            assert child.engineering_state==CONFIRMED_STATUS

    def test_5_branch_only_product(self):
        product = self.create_product_product("test_5_branch_only_product")
        product = product.product_tmpl_id 
        product.new_branch()
        children_branch = product.children_branch()
        assert len(children_branch)==1
        for child_branch in children_branch:
            assert child_branch.engineering_branch_revision==0
            assert child_branch.engineering_revision==1
            assert child_branch.engineering_sub_revision_letter=="0.0"
            child_branch.new_branch()
            children_branch_1 = child_branch.children_branch()
            assert len(children_branch_1)==1
            for child_branch_1 in children_branch_1:
                assert child_branch_1.engineering_branch_revision==0
                assert child_branch_1.engineering_revision==2
                assert child_branch_1.engineering_sub_revision_letter=="0.0.0"
                break
            break
        #
        for child_branch in children_branch:
            new_version_1 = child_branch._new_branch_version() # "0.1"
            assert new_version_1.engineering_revision==3
            assert new_version_1.engineering_branch_revision==1
            assert new_version_1.engineering_sub_revision_letter=="0.1"
            #
            child_branch_level = child_branch.get_latest_level_branch_revision()
            assert new_version_1.id == child_branch_level.id
            #
            new_version_2 = child_branch._new_branch_version()
            assert new_version_2.engineering_revision==4
            assert new_version_1.id < new_version_2.id
            assert new_version_2.engineering_branch_revision==2
            assert new_version_2.engineering_sub_revision_letter=="0.2"        
            #
            child_branch_level = child_branch.get_latest_level_branch_revision()
            assert new_version_2.id == child_branch_level.id
#
    