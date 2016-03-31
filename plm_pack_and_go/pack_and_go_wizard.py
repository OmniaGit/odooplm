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
Created on Mar 30, 2016

@author: Daniel Smerghetto
'''
import logging
from openerp import models, fields, api, SUPERUSER_ID, _, osv
import tempfile
import base64
import os
import shutil
_logger = logging.getLogger(__name__)


class PackAndGo(osv.osv.osv_memory):
    _name = 'pack.and_go'
    _inherit='ir.attachment'

    def setComponentFromContext(self):
        """
            set the default value from getting the value from the context
        """
        return self._context.get('active_id', 0)

    component_id    = fields.Many2one('product.product', _('Component'), default=setComponentFromContext)
    name            = fields.Char('Attachment Name', required=True, default=' '),
    type            = fields.Selection( [ ('url','URL'), ('binary','File'), ],
                'Type', help="You can either upload a file from your computer or copy/paste an internet link to your file", required=True, change_default=True, default='binary'),
                
    def computeDocFiles(self, compBrws, tmpSubFolder):
        outDocs = []
        for docBws in compBrws.linkeddocuments:
            outFilePath = os.path.join(tmpSubFolder, docBws.datas_fname)
            with open(outFilePath, 'wb') as outDocFile:
                outDocFile.write(docBws.datas)
            outDocs.append(outFilePath)
        return outDocs

    @api.multi
    def action_export_zip(self):
        """
            action to import the data
        """
        objBom = self.env['mrp.bom']
        objProduct = self.env['product.product']
        
        prodTmplId      = objBom.GetTmpltIdFromProductId(self.component_id.id)
        bomId           = objBom._getbom(prodTmplId)
        explosedBomIds  = objBom._explodebom(bomId, True)
        relDatas        = [self.ids[0], explosedBomIds]
        compIds         = objBom.getListIdsFromStructure(relDatas)
        
        tmpSubFolder = tempfile.mkdtemp()
        tmpSubSubFolder = os.path.join(tmpSubFolder, self.component_id.engineering_code)
        if not os.path.exists(tmpSubSubFolder):
            os.makedirs(tmpSubSubFolder)
        outDocPaths = []
        for compId in compIds:
            compBrws = objProduct.browse(compId)
            outDocPaths.extend(self.computeDocFiles(compBrws, tmpSubSubFolder))
            
        outZipFile = os.path.join(tempfile.gettempdir(), self.component_id.engineering_code)
        outZipFile = shutil.make_archive(outZipFile, 'zip', tmpSubFolder)

        with open(outZipFile, 'rb') as f:
            fileContent = f.read()
            if fileContent:
                self.datas = base64.encodestring(fileContent)
        fileName = os.path.basename(outZipFile)
        self.datas_fname = fileName
        self.name = fileName
        #self.store_fname = fileName
        return {'name': _('Pack and Go'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'pack.and_go',
                'target' : 'new',
                'res_id': self.ids[0],
                'type': 'ir.actions.act_window',
                'domain': "[]"}
PackAndGo()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: