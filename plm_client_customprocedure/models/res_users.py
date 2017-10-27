# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution    
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    $Id$
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
Created on Apr 19, 2017

@author: daniel
'''

from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import base64
import tempfile
import os


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    custom_read_content = fields.Text(_('Modif Content'), default='')
    custom_procedure = fields.Binary(string=_('Client CustomProcedure'))
    custom_procedure_fname = fields.Char(_("New File name"))

    @api.multi
    def getCustomProcedure(self):
        for userBrws in self.browse(self.env.uid):
            logging.info('Request CustomProcedure file for user %r' % (userBrws.env.uid))
            if userBrws.custom_procedure:
                return userBrws.custom_procedure, userBrws.custom_procedure_fname
            else:
                for groupBrws in userBrws.groups_id:
                    res, fileContent, fileName = groupBrws.getCustomProcedure()
                    if not res:
                        continue
                    else:
                        logging.info('Got CustomProcedure file from group %r-%r with ID %r' % (groupBrws.category_id.name, groupBrws.name, groupBrws.id))
                        return fileContent, fileName
        return '', ''
        
    @api.multi
    def open_custommodule_edit(self):
        for userBrws in self:
            self.commonCustomEdit(userBrws.custom_procedure)

    @api.model
    def commonCustomEdit(self, fileContent):
        if fileContent:
            fileReadableContent = base64.decodestring(fileContent)
            self.custom_read_content = fileReadableContent
     
    @api.multi
    def open_custommodule_save(self):
        for userBrws in self:
            userBrws.custom_procedure = base64.encodestring(self.custom_read_content.encode('utf-8'))
            tmpFolder = tempfile.gettempdir()
            if userBrws.custom_procedure_fname:
                customFilePath = os.path.join(tmpFolder, userBrws.custom_procedure_fname)
                with open(customFilePath, 'w') as writeFile:
                    writeFile.write(base64.decodestring(userBrws.custom_procedure))
            userBrws.custom_read_content = ''

