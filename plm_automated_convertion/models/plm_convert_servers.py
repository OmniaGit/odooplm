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
from odoo.exceptions import UserError
import requests


class PlmConvertServers(models.Model):
    _name = "plm.convert.servers"
    _description = "Servers of conversions"
    _order = 'sequence ASC'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Server Name')
    address = fields.Char('Server IP Address')
    protocol = fields.Char('Server Protocol', default='http')
    port = fields.Char('Server Port')
    proc_to_kill = fields.Char('Process To Kill')
    client_processes = fields.Text('Client Processes')
    timeout = fields.Float('Connection timeout', default=2)
    is_internal = fields.Boolean('The server is odoo itself', default=False)
    available_format = fields.One2many(comodel_name="plm.convert.format",
                                       inverse_name="server_id",
                                       string="Available Formats")
    folder_to = fields.Text("Folder To")
    available =  fields.Boolean("Is Available",
                                default=True)
    def getBaseUrl(self):
        for server in self:
            return '%s://%s:%s' % (server.protocol, server.address, server.port)
        return ''

    def getMainServer(self):
        return self.search([], order='sequence ASC', limit=1)

    @api.model
    def create(self, vals):
        ret = super(PlmConvertServers, self).create(vals)
        if not vals.get('sequence'):
            ret.sequence = ret.id
        return ret

    def getTimeOut(self):
        for server in self:
            if server.timeout:
                return server.timeout
            return 2

    def testConnection(self):
        for server in self:
            if not server.is_internal:
                base_url = server.getBaseUrl()
                url = base_url + '/odooplm/api/v1.0/isalive'
                try:
                    response = requests.get(url, timeout=self.getTimeOut())
                except Exception as ex:
                    raise UserError("Server not correctly defined. Error %r" % (ex))
                if response.status_code != 200:
                    raise UserError("Server not correctly defined")
                if response.text != 'OK':
                    raise UserError("Server not correctly defined")
        title = "Connection Test Succeeded!"
        message = "Everything seems properly set up!"
        return self.infoMessage(title, message)

    def infoMessage(self, title, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
            }
        }

    def killProcess(self):
        for server in self:
            if server.proc_to_kill and not server._is_internal:
                base_url = server.getBaseUrl()
                url = base_url + '/odooplm/api/v1.0/kill_process'
                params = {}
                params['pid'] = server.proc_to_kill
                try:
                    response = requests.post(url, params=params, timeout=self.getTimeOut())
                except Exception as ex:
                    raise UserError('Cannot kill process due to error %r' % (ex))
                if response.status_code != 200:
                    raise UserError('Cannot kill process %r' % (response.status_code))
        title = "Process Killed Succeeded!"
        message = "Everything went ok!"
        server.client_processes = ''
        return self.infoMessage(title, message)

    def getClientProcesses(self):
        for server in self:
            if not server._is_internal:
                base_url = server.getBaseUrl()
                url = base_url + '/odooplm/api/v1.0/get_processes_details'
                try:
                    response = requests.get(url, timeout=self.getTimeOut())
                except Exception as ex:
                    raise UserError("Cannot get process list. Error %r" % (ex))
                if response.status_code != 200:
                    raise UserError("Wrong responce from server %r" % (response.status_code))
                res = response.json()
                outMsg = ''
                for procId, procVals in res.items():
                    outMsg += 'Proc ID %r\n' % (procId)
                    outMsg += '    Name %r\n' % (procVals.get('name', ''))
                    outMsg += '    Exe %r\n' % (procVals.get('exe', ''))
                    outMsg += '    Working Dir %r\n\n' % (procVals.get('directory', ''))
            else:
                outMsg = "Internal odoo server no process needed"
            server.client_processes = outMsg
    
    def updateAvailableFormat(self):
        """
        call the cad server in order to retreive the available formats
        """
        try:
            obj_format= self.env['plm.convert.format']
            url = '%s//%s:%s/odooplm/api/v1.0/getAvailableExtention' % (self.address, 
                                                                        self.protocol,
                                                                        self.port ) 
            response = requests.get(url)
            if response.status_code != 200:
                raise UserError("Conversion of cad server failed, check the cad server log")
            ret = response.json()
            #'.e2': ('thinkdesign', ['.dxf', '.dwg', '.igs', '.d', '.pdf']),
            for from_format, values in ret.items():
                cad_name, convertion_to_formats = values
                for format_to in convertion_to_formats:
                    if not self.available_format.filtered(lambda x: x.start_format==from_format and x.end_format==format_to and x.cad_name==cad_name):
                        obj_format.sudo().create({'start_format':from_format,
                                                  'end_format':format_to,
                                                  'cad_name':cad_name,
                                                  'server_id': self.id,
                                                  'available': True})
                
        except Exception as ex:
            self.error_message = "%s" % ex

        
