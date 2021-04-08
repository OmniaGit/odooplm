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
import base64
import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.modules.module import get_module_resource
import urllib.parse
SUPPORTED_WEBGL_EXTENTION = ['.gltf','.glb','.fbx']

def getWebGlBase64():
    file_path = get_module_resource('plm_web_3d_sale',
                                    'static/src/img',
                                    'webgl3d.png')
    return base64.b64encode(open(file_path, 'rb').read())
        
        
        
class ProductImage(models.Model):
    _inherit = ['product.image']
    
    ir_attachment_webgl_id = fields.Many2one('ir.attachment', 
                                             string='Documenti Collegati',
                                             domain=[('has_web3d', '=', True),
                                                     ('public', '=', True)])

    def _compute_embed_code(self):
        super(ProductImage, self)._compute_embed_code()
        for image in self:
            url = image.ir_attachment_webgl_id.get_url_for_3dWebModel()
            if url:
                image.embed_code = '<iframe id="embedded_odoo_plm_webgl" src="%s"></iframe>' % url #.replace("http:","").replace("https:","")
            
    @api.onchange('ir_attachment_webgl_id')
    def attach_preview(self):
        for product_image in self:
            if self.ir_attachment_webgl_id:
                stream = self.ir_attachment_webgl_id.preview
                if not stream:
                    stream = getWebGlBase64()
                product_image.image_1920 = stream
            
#    def get3dWebGl(self):
#        for image in self:
#            url = image.ir_attachment_webgl_id.get_url_for_3dWebModel()
#            if url:
#                return '<iframe class="embed-responsive-item" allowFullScreen="true" frameborder="0" src="%s"></iframe>' % url
#        return '<p></p>'
    