# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from osv import fields, osv
from tools import config

import base64
import addons
import difflib

class plm_installer(osv.osv_memory):
    _name='plm.installer'
    _inherit='res.config.installer'
    __logger = logging.getLogger(_name)

    def default_get(self, cr, uid, fields, context=None):
        data=super(plm_installer, self).default_get(cr, uid, fields, context)
        data['exe_file']='http://sourceforge.net/projects/openerpplm/files/Client/ClientIntegration/OpenErpPlm.exe/download'
        return data

    _columns={
        'name':fields.char('File name', size=34),
        'exe_name':fields.char('File name', size=128),
        'openerpplm':fields.boolean('OpenErp PLM Plug-in', help="Product Life-Cycle Management Module."),
        'exe_file':fields.char('OpenErp PLM File download', size=128, readonly=True, help="Product Life-Cycle Management Client file. Save this file and install this application."),
        'description':fields.text('Description', readonly=True)
    }

    _defaults={
        'openerpplm' : False,
        'name' : 'OpenErpPlm.exe',
        'description' : """
        To complete your installation follow these notes :
         
        * Configure OpenErp access capabilty adding Users to the group 'PLM / Integration' before to use Clients.
        
        * Download the OpenErp PLM Client file.
        * Follow these steps to install Product Life-Cycle Management Client.
            1. Double click on OpenErp PLM Client file.
            2. Select language.
            3. Select the directory where to install integrations.
            4. Select the editor that has to be connected.
        
        * At editor startup OpenERP PLM menu and toolbar will be automatically loaded.
        * At first time execution :
            1. Click on Login button.
            2. Insert data connection.
        """
    }

plm_installer()