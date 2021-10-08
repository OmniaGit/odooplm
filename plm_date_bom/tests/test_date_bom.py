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

@tagged('-standard', 'plm_date_bom')
class PlmDateBom(TransactionCase):
    def test_some_action(cls):
        #
        # Product environment related data
        #
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
        MrpBom = cls.env['mrp.bom']                                                   
        cls.product_parent_id = Product.create({
            'name': 'test_parent_product',
            'engineering_code' : 'test_parent_product',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})
        cls.product_child_id = Product.create({
            'name': 'test_child_product',
            'engineering_code' : 'test_child_product',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})        
        cls.mrp_bom_id = MrpBom.create({'product_tmpl_id': cls.product_parent_id.product_tmpl_id.id,
                                                     'bom_line_ids': [
                                                         Command.create({
                                                             'product_id': cls.product_child_id.id,
                                                             'product_qty': 2,
                                                             })],
                                                     })
        #
        # release the product
        #
        cls.product_parent_id.action_confirm()
        cls.product_parent_id.action_release()
        for bom_line in cls.mrp_bom_id.bom_line_ids:
            cls.assertEqual(bom_line.product_id.state, 'released')
        newComponentId, engineering_revision = cls.product_child_id.NewRevision()
        cls.assertFalse(newComponentId==cls.product_child_id.id)
        cls.new_revision_child = Product.browse(newComponentId)
        cls.new_revision_child.action_confirm()
        cls.new_revision_child.action_release()  
        #
        # check bom changed
        #
        bom_to_update_ids = cls.mrp_bom_id._showAllBomsToCompute()
        cls.assertIn(cls.mrp_bom_id.id, bom_to_update_ids)
        cls.assertTrue(cls.mrp_bom_id.obsolete_presents)
        MrpBom.updateWhereUsed(cls.product_child_id)
        
              

    