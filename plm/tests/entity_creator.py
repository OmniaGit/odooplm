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
    
    def create_document(self, name, eng_code=False, doc_type='other'):
        if not eng_code:
            eng_code="eng_code_" + name
        ir_attachment= self.env['ir.attachment'].create({
            'datas': DUMMY_CONTENT,
            'name': name,
            'engineering_code': eng_code,
            'res_model': 'ir.attachment',
            'res_id': 0,
            'document_type':doc_type,
        })
        ir_attachment.document_type=doc_type
        return ir_attachment

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
    
    def create_product_document(self, name, doc_type='3d'):
        product = self.create_product_product("product_" + name)
        document = self.create_document(f"attachment_{doc_type}_{name}", doc_type=doc_type)
        document.linkedcomponents =[(4, product.id)]
        return product, document
    
    def create_product_document_with_layout_rfTree(self, name):
        product, document3D = self.create_product_document(name, '3d')
        document2D = self.create_document(f"attachment_2d_{name}" ,doc_type='2d')
        document2D.linkedcomponents =[(4, product.id)]
        documentRD = self.create_document(f"attachment_Rd3d_{name}",doc_type='3d')
        documentRD.linkedcomponents =[(4, product.id),'3d']
        self.create_link_document(document3D, document2D,'LyTree')
        self.create_link_document(document3D, documentRD,'RfTree')
        return product, document3D, document2D, documentRD
    
    def create_bom(self, parent, child, qty=1):
        parent_bom=None
        for parent_bom in self.env['mrp.bom'].search([('product_id','=', parent.id)]):
            break
        if not parent_bom:
            parent_bom = self.env['mrp.bom'].create({'product_id': parent.id,
                                                     'product_tmpl_id': parent.product_tmpl_id.id})
        self.env['mrp.bom.line'].create({'bom_id': parent_bom.id,
                                         'product_id': child.id,
                                         'product_qty': qty})
        return parent_bom
    
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
    
    def create_link_document(self, doc_parent, doc_child, link_kind):
        """
        :link_kind 
            link_kind == 'RfTree'  # Reference tree part and is part 
            link_kind == 'LyTree'  # Reference 2d with 3d
            link_kind == 'HiTree'  # Reference 3d with 3d normal tree
            link_kind == PkgTree'  # Reference package or support link
        """
        self.env['ir.attachment.relation'].create({'parent_id': doc_parent.id,
                                                   'child_id': doc_child.id,
                                                   'link_kind': link_kind})  
    def get_3_level_assembly(self, name=''):
        #
        product1, document3D1, document2D1, documentRD1 = self.create_product_document_with_layout_rfTree(f"{name}_Parent")
        product2, document3D2, document2D2, documentRD2 = self.create_product_document_with_layout_rfTree(f"{name}_Child_level_1")
        product3, document3D3, document2D3, documentRD3 = self.create_product_document_with_layout_rfTree(f"{name}_Child_level_1.1")
        product4, document3D4, document2D4, documentRD4 = self.create_product_document_with_layout_rfTree(f"{name}_Child_level_2")
        product5, document3D5, document2D5, documentRD5 = self.create_product_document_with_layout_rfTree(f"{name}_Child_level_2.1")
        #
        # create doc bom
        #
        self.create_link_document(document3D1,document3D2,'HiTree')
        self.create_link_document(document3D1,document3D4,'HiTree')
        self.create_link_document(document3D2,document3D3,'HiTree')
        self.create_link_document(document3D4,document3D5,'HiTree')
        #
        # create bom
        #
        main_bom = self.create_bom(product1,product2)
        self.create_bom(product1,product4)
        self.create_bom(product2,product3)
        self.create_bom(product4,product5)
        #
        return product1, main_bom
        
        