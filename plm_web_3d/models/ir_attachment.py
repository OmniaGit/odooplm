# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2020 https://OmniaSolutions.website
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
Created on 13 Nov 2020

@author: mboscolo
'''
import os
import json
import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import urllib.parse
SUPPORTED_WEBGL_EXTENTION = ['.3mf','.gltf','.glb','.fbx','.obj','.wrl','.json', '.stl','.svg', '.dxf']
#
#
class IrAttachment(models.Model):
    _inherit = ['ir.attachment']
    
    has_web3d = fields.Boolean(string="Has 3d Web link",
                               compute="_compute_web_3d_link",
                              # store=True,
                               help='Check if this document has related 3d web document')

    def isWebGl(self):
        for ir_attachment in self:
            if ir_attachment.name:
                _name, exte = os.path.splitext(ir_attachment.name)
                return exte.lower() in SUPPORTED_WEBGL_EXTENTION
        return False
    
    @api.depends('name')
    def _compute_web_3d_link(self):
        attach_relations = self.env['ir.attachment.relation']
        for ir_attachment in self:
            if ir_attachment.isWebGl():
                ir_attachment.has_web3d = True
                continue
            ir_attachment.has_web3d = attach_relations.search_count([('parent_id', '=', ir_attachment.id),
                                                                     ('link_kind','=','Web3DTree')])
        
    def get_url_for_3dWebModel(self):
        attach_relations = self.env['ir.attachment.relation']
        for ir_attachment in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url_params = None
            if ir_attachment.isWebGl():
                url_params = urllib.parse.urlencode({'document_id': ir_attachment.id,
                                                     'document_name': ir_attachment.name})
            else:
                for rel in attach_relations.search([('parent_id', '=', ir_attachment.id),
                                                    ('link_kind','=','Web3DTree')]):
                    
                    url_params = urllib.parse.urlencode({'document_id': rel.child_id.id,
                                                         'document_name': rel.child_id.name})
            if url_params:
                return f"{base_url}/plm/show_treejs_model?{url_params}"
    
    def show_releted_3d(self):
        for ir_attachment in self:
            url = ir_attachment.get_url_for_3dWebModel()
            if url:
                return {'name': 'Odoo TreeJs View',
                        'res_model': 'ir.actions.act_url',
                        'type': 'ir.actions.act_url',
                        'target': self,
                        'url': url
                        }

    def get_all_relation(self, document_id, exte):
        out={}
        if exte in document_id.name:
            out[document_id.id] = document_id.name
        for child_attachment_id in self.getRelatedHiTree(document_id.id):
            if exte in self.browse(child_attachment_id).name:
                out[child_attachment_id.id]=child_attachment_id.name
        return out
     
    def get_document_relation_dict(self, document_id, document_name):
        out = {}
        for ir_attachment in self.browse(document_id):
            _name, exte = os.path.splitext(ir_attachment.name)
            for product_product_id in ir_attachment.linkedcomponents:
                for att_id in product_product_id.linkeddocuments:
                    out.update(self.get_all_relation(att_id,exte))
                for sub_bom_children_id in product_product_id.bom_ids.bom_line_ids.mapped("product_id"):
                    for att_id in sub_bom_children_id.linkeddocuments:
                        out.update(self.get_all_relation(att_id,exte)) 
            #

        if not out:
            out = {document_id: document_name}
        else:
            if document_id in out:
                del out[document_id]
        return json.dumps(out)
        