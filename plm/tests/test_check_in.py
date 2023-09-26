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
# --test-tags=odoo_plm
#
#

#
@tagged('-standard', 'odoo_plm_check_in')
class PlmDateBom(TransactionCase, PlmEntityCreator):
        
    def test_check_in(self):
        level_0_3d = self.create_document('document_level_0_3d',doc_type='3d')
        level_0_3d.checkout('web', '-', True)
        level_0_2d = self.create_document('document_level_0_2d',doc_type='2d')
        level_0_2d.checkout('web', '-', True)
        level_0_2d_1 = self.create_document('document_level_0_2d_1',doc_type='2d')
        level_0_2d_1.checkout('web', '-', True)
        #
        self.create_link_document(level_0_3d,level_0_2d,'LyTree')
        self.create_link_document(level_0_3d,level_0_2d_1,'LyTree')
        
        level_1_3d = self.create_document('document_level_1_3d',doc_type='3d')
        level_1_3d.checkout('web', '-', True)
        level_1_3d_1 = self.create_document('document_level_1_3d_1',doc_type='3d')
        level_1_3d_1.checkout('web', '-', True)
        level_1_2d = self.create_document('document_level_1_2d',doc_type='2d')
        level_1_2d.checkout('web', '-', True)        
        
        self.create_link_document(level_1_3d,level_1_2d,'LyTree')
        self.create_link_document(level_0_3d,level_1_3d,'HiTree')
        self.create_link_document(level_0_3d,level_1_3d_1,'HiTree')
        
        level_2_3d = self.create_document('document_level_2_3d',doc_type='3d')
        level_2_3d.checkout('web', '-', True)
        level_2_2d = self.create_document('document_level_2_2d',doc_type='2d')
        level_2_2d.checkout('web', '-', True)        
        
        self.create_link_document(level_2_3d,level_2_2d,'LyTree')
        self.create_link_document(level_1_3d,level_2_3d,'HiTree')

        level_3_3d = self.create_document('document_level_3_3d',doc_type='3d')
        level_3_3d.checkout('web', '-', True)
        level_3_2d = self.create_document('document_level_3_2d',doc_type='2d')
        level_3_2d.checkout('web', '-', True)
        
        self.create_link_document(level_3_3d,level_3_2d,'LyTree')
        self.create_link_document(level_2_3d,level_3_3d,'HiTree')
        
        res = level_0_3d._preCheckInRecursive_all(level_0_3d)
        assert len(res['to_check_2d'])==5
        assert len(res['to_check_3d'])==5
        assert len(res['info'])==0
        
        level_3_2d._check_in()
        res = level_0_3d._preCheckInRecursive_all(level_0_3d)
        assert len(res['to_check_2d'])==4
        assert len(res['to_check_3d'])==5
        assert len(res['info'])==1

        level_3_2d.checkout('web', '-', True, user_id=self.env.ref('base.default_user').id)
        res = level_0_3d._preCheckInRecursive_all(level_0_3d)
        assert len(res['to_check_2d'])==4
        assert len(res['to_check_3d'])==5
        assert len(res['info'])==1
        
        
                
