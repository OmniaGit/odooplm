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
Created on 9 Set 2023

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
# --test-tags=odoo_pack_and_go
#
#

#
@tagged('-standard', 'odoo_pack_and_go')
class PlmDateBom(TransactionCase, PlmEntityCreator):
        
    def test_pack_and_go(self):
        product, _bom = self.get_3_level_assembly("pack_and_go")
        other_attachment = self.create_document("parent_other_attachment")
        other_attachment.linkedcomponents =[(4, product.id)]
        pack_and_go_id = self.env['pack.and_go'].create({'component_id': product.product_tmpl_id.id})
        for export_type in ['2d','3d','pdf','2dpdf','3dpdf','3d2d','all']:
            pack_and_go_id.export_type=export_type
            pack_and_go_id.bom_computation = 'ONLY_PRODUCT'
            pack_and_go_id.action_compute_attachment_bom()
            if export_type=='2d':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='3d':
                assert len(pack_and_go_id.export_3d)==10, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='pdf':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='2dpdf':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='3d2d':
                assert len(pack_and_go_id.export_3d)==10, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='all':
                assert len(pack_and_go_id.export_3d)==10, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            pack_and_go_id.bom_computation = 'FIRST_LEVEL'
            pack_and_go_id.action_compute_attachment_bom()
            if export_type=='2d':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='3d':
                assert len(pack_and_go_id.export_3d)==8, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='pdf':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='2dpdf':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='3d2d':
                assert len(pack_and_go_id.export_3d)==8, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='all':
                assert len(pack_and_go_id.export_3d)==8, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            pack_and_go_id.bom_computation = 'ALL_LEVEL'
            pack_and_go_id.action_compute_attachment_bom()
            if export_type=='2d':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==5, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='3d':
                assert len(pack_and_go_id.export_3d)==10, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='pdf':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==5, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='2dpdf':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==5, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==5, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='3d2d':
                assert len(pack_and_go_id.export_3d)==10, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==5, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='all':
                assert len(pack_and_go_id.export_3d)==10, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert len(pack_and_go_id.export_2d)==5, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert len(pack_and_go_id.export_pdf)==5, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert len(pack_and_go_id.export_other)==1, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            pack_and_go_id.bom_computation = 'LEAF'
            pack_and_go_id.action_compute_attachment_bom()
            if export_type=='2d':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='3d':
                assert len(pack_and_go_id.export_3d)==4, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='pdf':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='2dpdf':
                assert len(pack_and_go_id.export_3d)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='3d2d':
                assert len(pack_and_go_id.export_3d)==4, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type=='all':
                assert len(pack_and_go_id.export_3d)==4, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"   
                assert len(pack_and_go_id.export_2d)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"   
                assert len(pack_and_go_id.export_pdf)==2, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"  
                assert len(pack_and_go_id.export_other)==0, f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"

        
                
