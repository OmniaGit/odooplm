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
    def getCadAndConvertionAvailabe(self, fromExtention, main_server=False, timeout_sec=False, raiseErr=False):
        void_ret = ('', [])
        try:
            if not main_server:
                main_server = self.env['plm.convert.servers'].getMainServer()
            base_url = main_server.getBaseUrl()
            timeout = main_server.getTimeOut()
            if timeout_sec:
                timeout = timeout_sec
            url = base_url + '/odooplm/api/v1.0/getAvailableExtention'
            response = requests.get(url, timeout=timeout)
            if response.status_code != 200:
                raise UserError("Conversion of cad server failed, check the cad server log")
            return response.json().get(str(fromExtention).lower(), void_ret)
        except Exception as ex:
            logging.error(ex)
            if raiseErr:
                raise Exception(ex)
            return void_ret

    @api.model
    def getAllFiles(self, document):
        out = {}
        attachment = self.env['ir.attachment']
        out['root_file'] = (document.name, document.datas)
        request = (document.id, [], -1, '', '')
        for outId, _, _, _, _, _ in attachment.CheckAllFiles(request):
            if outId == document.id:
                continue
            child_document = attachment.browse(outId)
            out[child_document.name] = child_document.datas
        return out

    @api.model
    def getFileConverted(self,
                         document,
                         targetIntegration,
                         targetExtention,
                         newFileName,
                         raiseError=True,
                         main_server=False):
        error = ''
        if not main_server:
            main_server = self.env['plm.convert.servers'].getMainServer()
        base_url = main_server.getBaseUrl()
        url = base_url + '/odooplm/api/v1.0/saveas'
        params = {}
        params['targetExtention'] = targetExtention
        params['integrationName'] = targetIntegration
        try:
            response = requests.post(url,
                                     params=params,
                                     files=self.getAllFiles(document))
        except Exception as ex:
            return '', ex
        if response.status_code != 200:
            try:
                err = 'Cannot convert file %r due to error %r' % (document, response.content.decode('utf-8'))
                logging.error(err)
                error = err
            except Exception as _ex:
                err = 'Cannot convert file %r' % (document, response.content.decode('utf-8'))
                logging.error(err)
                error = err
            if raiseError:
                raise UserError("Conversion of cad server failed, check the cad server log")
        newTarget = os.path.join(tempfile.gettempdir(), newFileName)
        if not error:
            with open(newTarget, 'wb') as f:
                f.write(response.content)
        return newTarget, error

    @api.model
    def calculate_available_extention(self):
        """
        calculate the conversion extension
        """
        name = self.env.context.get('name', False)
        active_id = self.env.context.get('active_id', False)
        active_model = self.env.context.get('active_model', False)
        if not name:
            if active_id and active_model and active_model == 'ir.attachment':
                name = self.env[active_model].browse(active_id).name
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
            newFilePath, _ = brwWizard.getFileConverted(brwWizard.document_id,
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
                                'datas_fname': os.path.basename(convertedFile)})
                    break
            break
        return {'name': _('File Converted'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': self._name,
                'target': 'new',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
                'domain': "[]"}
