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
@tagged('-standard', 'plm_automatic_weight')
class PlmDateBom(TransactionCase,PlmEntityCreator):
    
                    
    def test_product_attachment_wk(self):
        #
        # product
        #
        p_product, p_product1, p_product2, parent_bom, child_bom = self.create_bom_2_level("test_product_attachment_wk")
        # 
        # use_net
        #
        p_product.automatic_compute_selection='use_net'
        p_product.weight=10
        p_product1.automatic_compute_selection='use_net'
        p_product1.weight=20
        p_product2.automatic_compute_selection='use_net'
        p_product2.weight=30
        p_product.compute_bom_weight()
        assert p_product.weight==10
        #
        # use_cad
        #
        p_product.automatic_compute_selection='use_cad'
        p_product.weight=0
        p_product.weight_cad=10
        p_product1.automatic_compute_selection='use_cad'
        p_product1.weight=0
        p_product1.weight_cad=20
        p_product2.automatic_compute_selection='use_cad'
        p_product2.weight=0
        p_product2.weight_cad=30
        p_product.compute_bom_weight()
        assert p_product.weight==10
        #
        # use_normal_bom
        #
        p_product.automatic_compute_selection='use_normal_bom'
        p_product.weight=11
        p_product.weight_cad=10
        p_product1.automatic_compute_selection='use_normal_bom'
        p_product1.weight=22
        p_product1.weight_cad=20
        p_product2.automatic_compute_selection='use_normal_bom'
        p_product2.weight=33
        p_product2.weight_cad=30
        p_product.compute_bom_weight()
        assert p_product.weight==30
        #
        # use_normal_bom + weight_additional
        #
        p_product.automatic_compute_selection='use_normal_bom'
        p_product.weight=11
        p_product.weight_cad=10
        p_product2.weight_additional=5
        p_product1.automatic_compute_selection='use_normal_bom'
        p_product1.weight=22
        p_product1.weight_cad=20
        p_product2.weight_additional=5
        p_product2.automatic_compute_selection='use_normal_bom'
        p_product2.weight=33
        p_product2.weight_cad=30
        p_product2.weight_additional=5
        p_product.compute_bom_weight()
        assert p_product.weight==45
        