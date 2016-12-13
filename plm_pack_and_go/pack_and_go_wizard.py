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
from openerp import tools
import base64
import os
import shutil
_logger = logging.getLogger(__name__)


class PackAndGo(osv.osv.osv_memory):
    _name = 'pack.and_go'
    _inherit = 'ir.attachment'

    def setComponentFromContext(self):
        """
            set the default value from getting the value from the context
        """
        return self._context.get('active_id', 0)

    component_id = fields.Many2one('product.product', _('Component'), default=setComponentFromContext)
    name = fields.Char('Attachment Name', required=True, default=' ')
    type = fields.Selection([('url', 'URL'), ('binary', 'File')], 'Type', help="You can either upload a file from your computer or copy/paste an internet link to your file", required=True, change_default=True, default='binary')

    def computeDocFiles(self, compBrws, tmpSubFolder, filestorePath=''):
        for docBws in compBrws.linkeddocuments:
            if filestorePath:
                fileName = os.path.join(filestorePath, self.env.cr.dbname, docBws.store_fname)
                if os.path.exists(fileName):
                    outFilePath = os.path.join(tmpSubFolder, docBws.datas_fname)
                    shutil.copyfile(fileName, outFilePath)

    @api.multi
    def action_export_zip(self):
        """
            action to import the data
        """
        objBom = self.env['mrp.bom']
        objProduct = self.env['product.product']
        prodTmplId = self.component_id.product_tmpl_id.id
        bomId = objBom._getbom(prodTmplId)
        explosedBomIds = objBom._explodebom(bomId, True)
        relDatas = [self.component_id.id, explosedBomIds]
        compIds = objBom.getListIdsFromStructure(relDatas)
        tmpSubFolder = tools.config.get('document_path', os.path.join(tools.config['root_path'], 'filestore'))
        logging.info("Pack Go sub folder is %r" % tmpSubFolder)
        tmpSubSubFolder = os.path.join(tmpSubFolder, 'export', self.component_id.engineering_code)
        if not os.path.exists(tmpSubSubFolder):
            os.makedirs(tmpSubSubFolder)
        for compId in compIds:
            compBrws = objProduct.browse(compId)
            self.computeDocFiles(compBrws, tmpSubSubFolder, tmpSubFolder)
        outZipFile = os.path.join(tmpSubFolder, 'export_zip', self.component_id.engineering_code)
        outZipFile = shutil.make_archive(outZipFile, 'zip', tmpSubSubFolder)
        with open(outZipFile, 'rb') as f:
            fileContent = f.read()
            if fileContent:
                self.datas = base64.encodestring(fileContent)
        try:
            shutil.rmtree(tmpSubSubFolder)
            shutil.rmtree(fileContent)
        except Exception, ex:
            logging.error("Enable to delete file from export function %r %r" % (tmpSubSubFolder, unicode(ex)))
        fileName = os.path.basename(outZipFile)
        self.datas_fname = fileName
        self.name = fileName
        return {'name': _('Pack and Go'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'pack.and_go',
                'target': 'new',
                'res_id': self.ids[0],
                'type': 'ir.actions.act_window',
                'domain': "[]"}

PackAndGo()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
