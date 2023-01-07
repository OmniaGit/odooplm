# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solution
#    Copyright (C) 2011-2022 https://OmniaSolutions.website
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
Created on 4 Nov 2022

@author: mboscolo
'''

import logging

DUMMY_CONTENT = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="

class PlmEntityCreator(object):

    def create_uom(self):
        Uom = self.env['uom.uom']
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.uom_dozen = self.env.ref('uom.product_uom_dozen')
        self.uom_dunit = Uom.create({
            'name': 'DeciUnit',
            'category_id': self.uom_unit.category_id.id,
            'factor_inv': 0.1,
            'factor': 10.0,
            'uom_type': 'smaller',
            'rounding': 0.001})
        self.uom_weight = self.env.ref('uom.product_uom_kgm')
    
    def create_product_template(self, name):
        ProductTemplate = self.env['product.template']
        default_data = ProductTemplate.default_get(['uom_id','uom_po_id','sale_line_warn'])
        default_data.update({
            'name': name,
            })       
        if 'sale_line_warn' in ProductTemplate._fields.keys():
            default_data['sale_line_warn']='no-message'    
        try:
            ret = ProductTemplate.create(default_data)
        except Exception as ex:
            raise ex
        return ret 
    
    def create_product_product(self, name, eng_code=False):
        if not eng_code:
            eng_code="eng_code_PP_" + name
        product_tmpl = self.create_product_template(eng_code)
        product_tmpl.engineering_code=eng_code
        for pp in self.env['product.product'].search([('product_tmpl_id','=',product_tmpl.id)]):
            return pp
    
    def create_document(self, name, eng_code=False):
        if not eng_code:
            eng_code="eng_code_" + name
        return self.env['ir.attachment'].create({
            'datas': DUMMY_CONTENT,
            'name': name,
            'engineering_code': eng_code,
            'res_model': 'ir.attachment',
            'res_id': 0,
        })
    
    def create_bom_2_level(self, name):
        p_product = self.create_product_product("parent" + name)
        p_product1 = self.create_product_product("child_1" + name)
        p_product2 = self.create_product_product("child_2" + name)
        parent_bom = self.env['mrp.bom'].create({'product_id': p_product.id,
                                                 'product_tmpl_id': p_product.product_tmpl_id.id})
        self.env['mrp.bom.line'].create({'bom_id': parent_bom.id,
                                         'product_id': p_product1.id,
                                         'product_qty': 1})
        child_bom = self.env['mrp.bom'].create({'product_id': p_product1.id,
                                                'product_tmpl_id': p_product1.product_tmpl_id.id})
        self.env['mrp.bom.line'].create({'bom_id': child_bom.id,
                                         'product_id': p_product2.id,
                                         'product_qty': 1})
        return p_product, p_product1, p_product2, parent_bom, child_bom
    
    def create_product_document(self, name):
        product = self.create_product_product("product_" + name)
        document = self.create_document("attachment_" + name)
        document.linkedcomponents =[(4, product.product_tmpl_id.id)]
        return product, document
    
    def create_bom_with_document(self, name):
        p_product, p_document = self.create_product_document("parent")
        c1_product, c1_document = self.create_product_document("child_1")
        c2_product, c2_document = self.create_product_document("child_2")
        
        parent_bom = self.env['mrp.bom'].create({'product_id': p_product.id,
                                                 'product_tmpl_id': p_product.product_tmpl_id.id})
        self.env['mrp.bom.line'].create({'bom_id': parent_bom.id,
                                         'product_id': c1_product.id,
                                         'product_qty': 1})
        child_bom = self.env['mrp.bom'].create({'product_id': c1_product.id,
                                                'product_tmpl_id': c1_product.product_tmpl_id.id})
        self.env['mrp.bom.line'].create({'bom_id': child_bom.id,
                                         'product_id': c2_product.id,
                                         'product_qty': 1})
        return parent_bom
        
        
        