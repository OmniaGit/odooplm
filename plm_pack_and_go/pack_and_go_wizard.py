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
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
from openerp import osv
from openerp import report
from openerp import tools
from openerp.exceptions import UserError
import os
import base64
import shutil
_logger = logging.getLogger(__name__)


class AdvancedPackView(models.Model):
    _name = 'pack_and_go_view'

    component_id = fields.Many2one('product.product', _('Component'))
    document_id = fields.Many2one('plm.document', _('Document'))
    comp_rev = fields.Integer(_('Component Revision'))
    doc_rev = fields.Integer(_('Document Revision'))
    preview = fields.Binary(_('Preview Content'))


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
    export_type = fields.Selection([('all', _('All BOM Documents')),
                                    ('only_drawings', _('Only Drawings')),
                                    ('only_pdf', _('Only PDF')),
                                    ('drawings_and_pdf', _('Drawings and PDF'))
                                    ], _('Export Type'), default='all')
    export_rel = fields.Many2many('pack_and_go_view', 'table_pack_and_go_view', string=_('Select Rows to export'))

    @api.multi
    def clearAll(self):
        packAndGoViewObj = self.env['pack_and_go_view']
        objBrwsList = packAndGoViewObj.search([])
        objBrwsList.unlink()

    @api.multi
    def computeExportRelField(self):
        '''
            Populate related field with all components and documents of Bill of Materials
        '''
        self.clearAll()
        self.export_rel = []
        objProduct = self.env['product.product']
        objPackView = self.env['pack_and_go_view']
        viewObjs = []
        compIds = self.getBomCompIds()
        for compBrws in objProduct.browse(compIds):
            for docBrws in compBrws.linkeddocuments:
                newViewObj = objPackView.create({'component_id': compBrws.id,
                                                 'comp_rev': compBrws.engineering_revision,
                                                 'doc_rev': docBrws.revisionid,
                                                 'document_id': docBrws.id,
                                                 'preview': docBrws.preview,
                                                 })
                viewObjs.append(newViewObj.id)
        self.export_rel = viewObjs
        return {'name': _('Pack and Go'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'pack.and_go',
                'target': 'new',
                'res_id': self.ids[0],
                'type': 'ir.actions.act_window',
                'domain': "[]"}

    def getBomFromTemplate(self, prodTmpl):
        bomBrwsList = prodTmpl.bom_ids
        for bomBrws in bomBrwsList:
            if bomBrws.type == 'ebom':
                return [bomBrws]
        if bomBrwsList:
            return [bomBrwsList[0]]
        return []

    def getBomCompIds(self):
        '''
            Get all components composing the Bill of Materials
        '''
        def recursion(bomBrwsList):
            outCompIds = []
            for bomBrws in bomBrwsList:
                for bomLineBrws in bomBrws.bom_line_ids:
                    prodId = bomLineBrws.product_id.id
                    if prodId in outCompIds:
                        continue
                    prodTmplBrws = bomLineBrws.product_id.product_tmpl_id
                    bomBrwsList = self.getBomFromTemplate(prodTmplBrws)
                    lowLevelCompIds = recursion(bomBrwsList)
                    outCompIds.extend(lowLevelCompIds)
                    outCompIds.append(prodId)
            return list(set(outCompIds))

        startingBom = self.getBomFromTemplate(self.component_id.product_tmpl_id)
        if not startingBom:
            return
        compIds = recursion(startingBom)
        compIds.append(self.component_id.id)
        return compIds

    def getAll(self):
        '''
            Get all documents of the bill of materials
        '''
        docIds = []
        for viewObj in self.export_rel:
            docId = viewObj.document_id.id
            if docId not in docIds:
                docIds.append(docId)
        return docIds

    def getAllDrawings(self):
        '''
            Get document ids of all drawings in the assembly
        '''
        docIds = []
        plmDocRel = self.env['plm.document.relation']
        for viewObj in self.export_rel:
            docId = viewObj.document_id.id
            docRelBrws = plmDocRel.search([('child_id', '=', docId),
                                           ('link_kind', '=', 'LyTree')
                                           ])
            if docRelBrws:
                if docId not in docIds:
                    docIds.append(docId)
        return docIds

    def generateTmpFolder(self):
        '''
            Create temporary folder
        '''
        tmpSubFolder = tools.config.get('document_path', os.path.join(tools.config['root_path'], 'filestore'))
        logging.info("Pack Go sub folder is %r" % tmpSubFolder)
        tmpSubSubFolder = os.path.join(tmpSubFolder, 'export', self.component_id.engineering_code)
        if not os.path.exists(tmpSubSubFolder):
            os.makedirs(tmpSubSubFolder)
        return tmpSubFolder, tmpSubSubFolder

    @api.multi
    def action_export_zip(self):
        """
            action to import the data
        """
        docIds = []
        if self.export_type == 'all':
            docIds = self.getAll()
        elif self.export_type == 'only_drawings' or self.export_type == 'only_pdf' or self.export_type == 'drawings_and_pdf':
            docIds = self.getAllDrawings()
        if not docIds:
            raise UserError(_('No documents found.'))
        tmpSubFolder, tmpSubSubFolder = self.generateTmpFolder()
        self.computeDocFiles(docIds, tmpSubSubFolder, tmpSubFolder)
        # Make archive, upload it and clean
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

    def computeDocFiles(self, docIds, tmpSubFolder, filestorePath=''):
        '''
            Generate PDF and save documents in the temporary folder
        '''
        for docBws in self.env['plm.document'].browse(docIds):
            if self.export_type == 'only_pdf' or self.export_type == 'drawings_and_pdf':
                srv = report.interface.report_int._reports['report.' + 'plm.document.pdf']
                datas, fileExtention = srv.create(self.env.cr, self.env.uid, [docBws.id], False, context=self.env.context)
                outFilePath = os.path.join(tmpSubFolder, docBws.name + '.' + fileExtention)
                fileObj = file(outFilePath, 'wb')
                fileObj.write(datas)
            if filestorePath and self.export_type != 'only_pdf':
                fileName = os.path.join(filestorePath, self.env.cr.dbname, docBws.store_fname)
                if os.path.exists(fileName):
                    outFilePath = os.path.join(tmpSubFolder, docBws.datas_fname)
                    shutil.copyfile(fileName, outFilePath)

PackAndGo()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
