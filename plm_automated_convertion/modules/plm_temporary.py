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
from odoo import models, fields, api, _, osv
from odoo import tools
from odoo.exceptions import UserError
import base64
import os
import shutil
import requests
_logger = logging.getLogger(__name__)


class plm_temporary_batch_converter(osv.osv.osv_memory):
    _name = 'plm.convert'
    _description = "Temp Class for batch converter"

    @api.model
    def getCadAndConvertionAvailabe(self, fromExtention):
        serverName = self.env['ir.config_parameter'].get_param('plm_convetion_server')
        if not serverName:
            raise Exception("Configure plm_convetion_server to use this functionality")
        url = 'http://%s/odooplm/api/v1.0/getAvailableExtention' % serverName
        response = requests.get(url)
        if response.status_code != 200:
            raise UserError("Conversion of cad server failed, check the cad server log")
        return response.json().get(str(fromExtention).lower(), ('', []))

    @api.model
    def getAllFiles(self, document):
        out = {}
        attachment = self.env['ir.attachment']
        full_file_path = document._full_path(document.store_fname)
        with open(full_file_path, 'rb') as root_file:
            out['root_file'] = (document.name, root_file.read())
        request = (document.id, [], -1, '', '')
        for outId, _, _, _, _, _ in attachment.CheckAllFiles(request):
            if outId == document.id:
                continue
            child_document = attachment.browse(outId)
            child_full_path = child_document._full_path(child_document.store_fname)
            with open(child_full_path, 'rb') as child_file:
                out[child_document.name] = child_file.read()
        return out

    @api.model
    def getFileConverted(self,
                         document,
                         targetIntegration,
                         targetExtention,
                         newFileName=False):
        serverName = self.env['ir.config_parameter'].get_param('plm_convetion_server')
        if not serverName:
            raise Exception("Configure plm_convetion_server to use this functionality")
        url = 'http://%s/odooplm/api/v1.0/saveas' % serverName
        params = {}
        params['targetExtention'] = targetExtention
        params['integrationName'] = targetIntegration
        response = requests.post(url,
                                 params=params,
                                 files=self.getAllFiles(document))
        if response.status_code != 200:
            try:
                logging.error('Cannot convert file %r due to error %r' % (document, response.content.decode('utf-8')))
            except Exception as _ex:
                logging.error('Cannot convert file %r' % (document, response.content.decode('utf-8')))
            raise UserError("Conversion of cad server failed, check the cad server log")
        if not newFileName:
            newFileName = document.name + targetExtention
        newTarget = os.path.join(tempfile.gettempdir(), newFileName)
        with open(newTarget, 'wb') as f:
            f.write(response.content)
        return newTarget

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
    targetFormat = fields.Selection(selection='calculate_available_extention',
                                    string='Conversion Format',
                                    required=True)
    downloadDatas = fields.Binary('Download',
                                  attachment=True)
    datas_fname = fields.Char("New File name")

    def convert(self):
        """
        convert the file in a new one
        """
        out = []
        for brwWizard in self:
            _, fileExtension = os.path.splitext(self.document_id.name)
            cadName, _ = brwWizard.getCadAndConvertionAvailabe(fileExtension)
            if not brwWizard.document_id:
                raise UserError('Cannot convert missing document! Select it!')
            clean_name, _ext = os.path.splitext(brwWizard.document_id.name)
            newFileName = clean_name + brwWizard.targetFormat
            newFilePath = brwWizard.getFileConverted(brwWizard.document_id,
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
        UserError(_("File Converted check the shared folder"))

    def action_create_convert_download(self):
        """
        Convert file in the given format and return it to the web page
        """
        for convertedFile in self.convert():
            with open(convertedFile, 'rb') as f:
                fileContent = f.read()
                if fileContent:
                    self.write({'downloadDatas': base64.b64encode(fileContent),
                                'name': os.path.basename(convertedFile)})
                    break
            break
        return {'name': _('File Converted'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': self._name,
                'target': 'new',
                'res_id': self.id[0],
                'type': 'ir.actions.act_window',
                'domain': "[]"}
