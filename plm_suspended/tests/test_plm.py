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
from odoo.addons.plm.models.plm_mixin import START_STATUS
from odoo.addons.plm.models.plm_mixin import CONFIRMED_STATUS
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUS
from odoo.addons.plm.models.plm_mixin import UNDER_MODIFY_STATUS
from odoo.addons.plm.models.plm_mixin import OBSOLATED_STATUS
#
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator
#
#
# --test-tags=odoo_plm
#
#
DUMMY_CONTENT = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
#
@tagged('-standard', 'odoo_plm_suspended')
class PlmDateBom(TransactionCase,PlmEntityCreator):
    
    def perform_check_suspend(self, obj):
        obj.action_suspend()
        assert obj.engineering_state==suspended, "wrong state %s" % product.engineering_state
        obj.action_unsuspend()
        assert obj.engineering_state==START_STATUS, "wrong state %s" % product.engineering_state
                    
    def test_product_attachment_wk(self):
        #
        # product
        #
        product = self.create_product_product("test_product_attachment_wk_p")
        self.perform_check_suspend(product)
        product.action_confirm()
        self.perform_check_suspend(product)
        product.action_release()
        self.perform_check_suspend(product)
        #
        # document
        #
        product = self.create_document("test_product_attachment_wk_d")
        self.perform_check_suspend(product)
        product.action_confirm()
        self.perform_check_suspend(product)
        product.action_release()
        self.perform_check_suspend(product)        
        
        