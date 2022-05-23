##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 25/mag/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''
Created on 25/mag/2016

@author: mboscolo
'''
import os
import logging
import base64
import shutil
import tempfile
import requests
#
from odoo import models, fields, api, _
from odoo import tools
from odoo.exceptions import UserError
#
_logger = logging.getLogger(__name__)
#
#
class plm_temporary_batch_converter(models.TransientModel):
    _name = 'plm.convert'
    _description = "Temporary Class for batch converter"

    document_id = fields.Many2one('ir.attachment',
                                  'Related Document',
                                  requite=True)
    
    targetFormat = fields.Many2one('plm.convert.format',
                                   'Conversion Format',
                                   requite=True)
    
    extention = fields.Char('Extension',
                            compute='get_ext')
    
    
    @api.onchange("document_id")
    def get_ext(self):
        for plm_convert_id in self:
            plm_convert_id.extention = os.path.splitext(plm_convert_id.document_id.name)[1].lower()

    def action_create_coversion(self):
        """
            convert the file to the give format
        """
        plm_stack = self._convert('TOSHARED')
        raise UserError(_("File Converted check the shared folder"))

    def _convert(self, mode):
        """
            create the conversion stack and perform the conversion
            :mode plm_stack.operation_type ['UPDATE','CONVERT','TOSHARED']
            :return: plm_stack object
        """
        if not self.targetFormat:
            raise UserError(_("Select a target format !!"))
        obj_stack = self.env['plm.convert.stack']
        plm_stack = obj_stack.search([('start_document_id','=', self.document_id.id),
                                            ('convrsion_rule','=', self.targetFormat.id), 
                                            ('conversion_done','=', False)])
        if not plm_stack:
            prod_categ = self.env['product.category']
            for comp in self.document_id.linkedcomponents:
                prod_categ = comp.categ_id
            plm_stack = obj_stack.create({
                'convrsion_rule': self.targetFormat.id,
                'start_document_id': self.document_id.id,
                'product_category': prod_categ.id,
                'operation_type': mode,
                })
        plm_stack.convert()
        return plm_stack   

    def action_create_convert_download(self):
        """
        Convert file in the given format and return it to the web page
        """
        plm_stack = self._convert('CONVERT')
        return {'name': _('File Converted'),
                'res_model': 'plm.convert.stack',
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'plm.convert.stack',
                'res_id': plm_stack.id,
                'type': 'ir.actions.act_window',
                'context': {}}
