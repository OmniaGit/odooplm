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
from odoo import _
import os
import logging
import base64
import json

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
    server_id = fields.Many2one('plm.convert.servers', 'Conversion Server', )
    operation_type = fields.Selection([('UPDATE', 'Update'),
                                      ('DOWNLOAD', 'Download'),
                                      ('CONVERT', 'Convert')],
                                     string='Operation Type',
                                     help="""
                                     Type of conversion operation
                                     Update: Perform an update to the given document (pdf, Bitmap)
                                     Download: Perform a conversion on the given format and download the file
                                     Convert: Convert the file in place on the stack object
                                     """)
    
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
        logging.info('generateConvertedDocuments started')
        toConvert =  self.search([('conversion_done', '=', False)], order='sequence ASC')
        for convertion in toConvert:
            try:
                if convertion.server_id.is_internal:
                    end_format = json.loads(convertion.end_format)
                    if 'png_pdf_update' in end_format:
                        convertion.start_document_id._updatePreview()
                    else:
                        convertion.error_string = _("unable to perform update format %s not available for conversion") % end_format
                else:
                    self._generateConvertedDocuments(conversion)
            except Exception as ex:
                logging.error(ex)
                convertion.error_string = _("Internal Error %s") % ex
            
    def _generateConvertedDocuments(self, convertion):
        plm_convert = self.env['plm.convert']
        try:
            cadName, _ = plm_convert.getCadAndConvertionAvailabe(convertion.start_format, convertion.server_id, raiseErr=True)
        except Exception as ex:
            convertion.error_string = ex
            return
        if not cadName:
            convertion.error_string = _('Cannot get CAD name')
            return
        if not convertion.start_document_id:
            convertion.error_string = _('Starting document not set')
            return
        document = convertion.start_document_id
        components = document.linkedcomponents.sorted(lambda line: line.engineering_revision)
        component = self.env['product.product']
        if components:
            component = components[0]
        rule = _("'%s_%s' % (document.name, document.revisionid)")
        if convertion.output_name_rule:
            rule = convertion.output_name_rule
        try:
            clean_name = eval(rule, {'component': component, 'document': document, 'env': self.env})
        except Exception as ex:
            convertion.error_string = _('Cannot evaluate rule %s due to error %r') % (rule, ex)
            return
        newFileName = clean_name + convertion.end_format
        newFilePath, error = plm_convert.getFileConverted(document,
                                                          cadName,
                                                          convertion.end_format,
                                                          newFileName,
                                                          False,
                                                          main_server=convertion.server_id)
        if error:
            convertion.error_string = error
            return
        if not os.path.exists(newFilePath):
            convertion.error_string = 'File not converted'
            return
        attachment = self.env['ir.attachment']
        target_attachment = self.env['ir.attachment']
        attachment_ids = attachment.search([('name', '=', newFileName)])
        content = ''
        logging.info('Reading converted file %r' % (newFilePath))
        if not os.path.exists(newFilePath):
            msg = _('Cannot find file %r') % (newFilePath)
            logging.error(msg)
            convertion.error_string = msg
            return
        with open(newFilePath, 'rb') as fileObj:
            content = fileObj.read()
        if content:
            logging.info('File size %r, content len %r' % (os.path.getsize(newFilePath), len(content)))
            encoded_content = base64.b64encode(content)
            if attachment_ids:
                attachment_ids.write({'datas': encoded_content,
                                      'source_convert_document': document.id
                                      })
                target_attachment = attachment_ids[0]
            else:
                target_attachment = attachment.create({
                    'linkedcomponents': [(6, False, document.linkedcomponents.ids)],
                    'name': newFileName,
                    'datas': encoded_content,
                    'state': convertion.start_document_id.state,
                    'is_plm': True,
                    'engineering_document_name': newFileName,
                    'is_converted_document': True,
                    'source_convert_document': document.id
                    })
            try:
                os.remove(newFilePath)
                logging.info('Removed file %r' % (newFilePath))
            except Exception as ex:
                logging.warning(ex)
        else:
            msg = _('Cannot convert document %r because no content is provided. Convert stack %r') % (document.id, convertion.id)
            logging.error(msg)
            convertion.error_string = msg
        convertion.end_document_id = target_attachment.id
        convertion.conversion_done = True
        convertion.error_string = ''
        self.env.cr.commit()
    logging.debug('generateConvertedDocuments ended')
