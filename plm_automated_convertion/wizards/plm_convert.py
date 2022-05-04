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

import logging
import tempfile
from odoo import models, fields, api, _
from odoo import tools
from odoo.exceptions import UserError
import base64
import os
import shutil
import requests
_logger = logging.getLogger(__name__)


class plm_temporary_batch_converter(models.TransientModel):
    _name = 'plm.convert'
    _description = "Temp Class for batch converter"

    @api.model
    def getAllFiles(self, document):
        out = {}
        ir_attachment = self.env['ir.attachment']
        fileStoreLocation = ir_attachment._get_filestore()

        def templateFile(docId):
            document = ir_attachment.browse(docId)
            return {document.name: (document.name,
                                    open(os.path.join(fileStoreLocation, document.store_fname), 'rb'))}
        out['root_file'] = (document.name,
                            open(os.path.join(fileStoreLocation, document.store_fname), 'rb'))
        objDocu = self.env['ir.attachment']
        request = (document.id, [], -1)
        for outId, _, _, _, _, _ in objDocu.CheckAllFiles(request):
            if outId == document.id:
                continue
            out.update(templateFile(outId))
        return out

    @api.model
    def calculate_available_extention(self):
        """
        calculate the conversion extension
        """
        name = self.env.context.get('name', False)
        if name:
            _, file_extension = os.path.splitext(name)
            _, avilableFormat = self.getCadAndConvertionAvailabe(file_extension)
            return [(a, a) for a in avilableFormat]
        return []

    document_id = fields.Many2one('ir.attachment',
                                  'Related Document')
    
    targetFormat = fields.Many2one('plm.convert.format', 'Conversion Format')
    
    extention = fields.Char('Extention', compute='get_ext')
    
    downloadDatas = fields.Binary('Download', attachment=True)
    
    datas_fname = fields.Char("New File name")
    
    batch_preview_printout = fields.Boolean('Batch convert preview and printout', default=False)
    
    error_message = fields.Text("Error")
    
    @api.onchange("document_id")
    def get_ext(self):
        for plm_convert_id in self:
            plm_convert_id.extention = os.path.splitext(plm_convert_id.document_id.name)[1]

    def convert(self):
        """
            convert the file in a new one
        """
        out = []
        for brwWizard in self:
            if brwWizard.batch_preview_printout:
                #
                # use internal convert tool
                #
                brwWizard.document_id.createPreview()
            else:
                #
                # call external convert tool for cad
                #
                _, fileExtension = os.path.splitext(self.document_id.name)
                cadName, _ = self.getCadAndConvertionAvailabe(fileExtension)
                newFileName = ''
                for component in brwWizard.document_id.linkedcomponents:
                    newFileName = component.engineering_code + brwWizard.targetFormat
                if newFileName == '':
                    newFileName = self.document_id.name + '.' + brwWizard.targetFormat
                newFilePath = self.getFileConverted(brwWizard.document_id,
                                                    cadName,
                                                    brwWizard.targetFormat,
                                                    newFileName)
                out.append(newFilePath)
        return out

    def action_create_coversion(self):
        """
        convert the file to the give format
        """
        convertionFolder = self.env['ir.config_parameter'].get_param('plm_convertion_folder')
        converted = self.convert()
        for newFilePath in converted:
            try:
                shutil.move(newFilePath, convertionFolder)
            except Exception:
                newFileName = os.path.join(convertionFolder, os.path.basename(newFilePath))
                os.remove(newFileName)
                shutil.move(newFilePath, convertionFolder)
        raise UserError(_("File Converted check the shared folder"))

    def action_create_convert_download(self):
        """
        Convert file in the given format and return it to the web page
        """
        obj_stack = self.env['plm.convert.stack']
        doc_id = self.env.context.get('active_id', False)
        doc_brws = self.env['ir.attachment'].browse(doc_id)
        server_id = self.targetFormat.server_id
        if not server_id:
            server_id = self.env.ref('plm_automated_convertion.odoo_local_server')
        plm_stack = obj_stack.search_count([('start_document_id', '=', doc_id),
                                            ('convrsion_rule', '=', self.targetFormat.id),
                                            ('conversion_done', '=', False)])
        if not plm_stack:
            prod_categ = self.env['product.category']
            for comp in doc_brws.linkedcomponents:
                prod_categ = comp.categ_id
            plm_stack = obj_stack.create({
                'convrsion_rule': self.targetFormat.id,
                'start_document_id': doc_id,
                'server_id': server_id.id,
                'product_category': prod_categ.id,
                'operation_type': 'CONVERT',
                })
        plm_stack.generateConvertedDocuments()
        return {'name': _('File Converted'),
                'res_model': obj_stack._name,
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': plm_stack._name,
                #'target': 'new',
                'res_id': plm_stack.id,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [obj_stack.id])],
                'context': {}}
