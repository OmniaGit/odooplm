# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
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
Created on Sep 7, 2019

@author: mboscolo
'''
from odoo import models
from odoo import fields
from odoo import api
import os


class PlmConvertStack(models.Model):
    _name = "plm.convert.stack"
    _description = "Stack of conversions"
    _order = 'sequence ASC'

    sequence = fields.Integer('Sequence')
    start_format = fields.Char('Start Format')
    end_format = fields.Char('End Format')
    product_category = fields.Many2one('product.category', 'Category')
    conversion_done = fields.Boolean('Conversion Done')
    start_document_id = fields.Many2one('ir.attachment', 'Starting Document')
    end_document_id = fields.Many2one('ir.attachment', 'Converted Document')
    output_name_rule = fields.Char('Output Name Rule')
    error_string = fields.Text('Error')
    
    def setToConvert(self):
        for convertStack in self:
            convertStack.conversion_done = False

    @api.model
    def create(self, vals):
        ret = super(PlmConvertStack, self).create(vals)
        if not vals.get('sequence'):
            ret.sequence = ret.id
        return ret

    def generateConvertedDocuments(self):
        toConvert =  self.search([('conversion_done', '=', False)], order='sequence ASC')
        for convertion in toConvert:
            plm_convert = self.env['plm.convert']
            cadName, _ = plm_convert.getCadAndConvertionAvailabe(convertion.start_format)
            if not cadName:
                convertion.error_string = 'Cannot get Cad name'
                continue
            if not convertion.start_document_id:
                convertion.error_string = 'Starting document not set'
                continue
            clean_name, _ext = os.path.splitext(convertion.start_document_id.name)
            newFileName = clean_name + convertion.end_format
            newFilePath, error = plm_convert.getFileConverted(convertion.start_document_id,
                                                       cadName,
                                                       convertion.end_format,
                                                       newFileName,
                                                       False)
            if error:
                convertion.error_string = error
                continue
            if not os.path.exists(newFilePath):
                convertion.error_string = 'File not converted'
                continue
            attachment = self.env['ir.attachment']
            target_attachment = self.env['ir.attachment']
            attachment_ids = attachment.search([('name', '=', newFileName)])
            with open(newFilePath, 'rb') as fileObj:
                content = fileObj.read()
                if attachment_ids:
                    attachment_ids.write({'datas': content})
                    target_attachment = attachment_ids[0]
                else:
                    target_attachment = attachment.create({
                        'linkedcomponents': [(6, False, convertion.start_document_id.linkedcomponents.ids)],
                        'name': newFileName,
                        'datas': content,
                        'state': convertion.start_document_id.state
                        })
            convertion.end_document_id = target_attachment.id
            convertion.conversion_done = True
