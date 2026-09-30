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
import base64

from odoo import api, fields, models
from odoo.tools.misc import file_path as fp

SUPPORTED_WEBGL_EXTENTION = ['.gltf','.glb','.fbx']

def getWebGlBase64():
    file_path = fp('plm_web_3d_sale/static/src/img/webgl3d.png')
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


class ProductImage(models.Model):
    _inherit = 'product.image'

    ir_attachment_webgl_id = fields.Many2one('ir.attachment',
                                             string='Documenti Collegati',
                                             domain=[('has_web3d', '=', True),
                                                     ('public', '=', True)])

    def _get_webgl_url(self):
        """URL of the 3D viewer of the linked document, or False.

        v20 core dropped `embed_code`: the shop page only embeds a `video_url`, so
        the 3D iframe is rendered by our own branch of `shop_product_image`. The
        document is read with sudo: the website visitor has no right on it, and
        the page must not fail because of it.
        """
        self.ensure_one()
        return self.sudo().ir_attachment_webgl_id.get_url_for_3dWebModel() or False

    @api.onchange('ir_attachment_webgl_id')
    def attach_preview(self):
        for product_image in self:
            if self.ir_attachment_webgl_id:
                stream = self.ir_attachment_webgl_id.preview
                if not stream:
                    stream = getWebGlBase64()
                product_image.image_1920 = stream
