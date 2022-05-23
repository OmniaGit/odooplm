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
import json
import tempfile
import logging
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo import tools
from odoo.exceptions import UserError
import os
import base64
import shutil
import requests
_logger = logging.getLogger(__name__)


class AvailableTypes(models.TransientModel):
    _name = 'pack_and_go_types'
    _description = "Description of pack and go"

    name = fields.Char(_('Name'))
    pack_and_go_view_id = fields.Many2one('pack_and_go_view')


class AdvancedPackView(models.TransientModel):
    _name = 'pack_and_go_view'
    _description = "Manage pack view for exporting"

    @api.model
    def _getComponentDescription(self):
        for row in self:
            row.comp_description = row.component_id.name

    @api.model
    def _getDocumentDescription(self):
        for row in self:
            row.document_description = row.document_id.name

    @api.model
    def _getDocumentFileName(self):
        for row in self:
            row.doc_file_name = row.document_id.name

    component_id = fields.Many2one('product.product', _('Component'))
    document_id = fields.Many2one('ir.attachment', _('Document'))
    comp_rev = fields.Integer(_('Component Revision'))
    comp_description = fields.Char(compute='_getComponentDescription')
    doc_rev = fields.Integer(_('Document Revision'))
    document_description = fields.Char(compute='_getDocumentDescription')
    doc_file_name = fields.Char(compute='_getDocumentFileName')
    preview = fields.Binary(_('Preview Content'))
    # Don't change keys because are used in a lower check in this file
    doc_type = fields.Selection([('2d', _('2D')),
                                 ('3d', _('3D')),
                                 ('other', _('Other')),
                                 ('pdf', _('PDF')),
                                 ], _('Document Type'))
    available_types = fields.Many2one('pack_and_go_types', _('Types'))
    pack_and_go_id = fields.Many2one('pack.and_go', _('Pack and go id'))


class PackAndGo(models.TransientModel):
    _name = 'pack.and_go'
    _description = "Main wizard collector for pack and go"

    def setComponentFromContext(self):
        """
            set the default value from getting the value from the context
        """
        return self._context.get('active_id', False)

    component_id = fields.Many2one('product.product',
                                   _('Component'),
                                   default=setComponentFromContext,
                                   required=True)
    name = fields.Char('Attachment Name',
                       required=True,
                       default=' ')
    type = fields.Selection([('url', 'URL'),
                             ('binary', 'File')],
                            'Type',
                            help="You can either upload a file from your computer or copy/paste an internet link to your file",
                            required=True,
                            change_default=True,
                            default='binary')
    export_type = fields.Selection([('2d', _('2D')),
                                    ('3d', _('3D')),
                                    ('pdf', _('PDF')),
                                    ('2dpdf', _('2D + PDF')),
                                    ('3dpdf', _('3D + PDF')),
                                    ('3d2d', _('3D + 2D')),
                                    ('all', _('2D + 3D + PDF')),
                                    ], _('Export Type'), default='all')
    export_3d = fields.Many2many('pack_and_go_view', 'export3d_pack', 'pack_view_id', 'pack_and_go_id', _('Select 3D Rows to export'))
    export_2d = fields.Many2many('pack_and_go_view', 'export2d_pack', 'pack_view_id', 'pack_and_go_id', _('Select 2D Rows to export'))
    export_pdf = fields.Many2many('pack_and_go_view', 'exportpdf_pack', 'pack_view_id', 'pack_and_go_id', _('Select PDF Rows to export'))
    export_other = fields.Many2many('pack_and_go_view', 'exportother_pack', 'pack_view_id', 'pack_and_go_id', _('Select Rows to export'))

    force_types_3d = fields.Many2one('pack_and_go_types', _('Force 3D Types'))
    force_types_2d = fields.Many2one('pack_and_go_types', _('Force 2D Types'))

    convertion_server_available = fields.Boolean(_('Conversion server available'), default=False)
    datas = fields.Binary(string="Download")
    datas_fname = fields.Char(string="File Name")

    def computeExportRelField(self, forceType=False):
        '''
            Populate related field with all components and documents of Bill of Materials
        '''
        self.clearAll()
        # Local colletions of ids, necessary to write in related fields
        export_2d = []
        export_3d = []
        export_other = []
        export_pdf = []
        checkedDocumentIds = []  # To know if the same document has been already analyzed
        objProduct = self.env['product.product']
        objPackView = self.env['pack_and_go_view']
        plmDocObject = self.env['ir.attachment']

        def docCheckCreate(doc, comp=False):
            compId = False
            compRev = False
            if comp:
                compId = comp.id
                compRev = comp.engineering_revision
            singleCreateDict = {'component_id': compId,
                                'comp_rev': compRev,
                                'doc_rev': doc.revisionid,
                                'document_id': doc.id,
                                'preview': doc.preview,
                                'available_types': False,
                                'doc_type': doc.document_type,
                                }
            if doc.document_type == '2d':
                if self.export_type in ('2d', '2dpdf', '3d2d', 'all'):
                    newViewObj = objPackView.create(singleCreateDict)
                    export_2d.append(newViewObj.id)
                if self.export_type in ('2dpdf', 'pdf', '3dpdf', 'all'):
                    singleCreateDict['doc_type'] = 'pdf'
                    newViewObj = objPackView.create(singleCreateDict)
                    export_pdf.append(newViewObj.id)
            elif doc.document_type == '3d':
                if self.export_type in ('3d', '3dpdf', '3d2d', 'all'):
                    newViewObj = objPackView.create(singleCreateDict)
                    export_3d.append(newViewObj.id)
            else:
                newViewObj = objPackView.create(singleCreateDict)
                export_other.append(newViewObj.id)

        def recursionDocuments(docBrwsList):
            for docBrws in docBrwsList:          
                res = plmDocObject.CheckAllFiles([docBrws.id, [],
                                                  False,
                                                  'localhost',
                                                  'pack_go'])   # Get all related documents to root documents
                for singleRes in res:
                    docId = singleRes[0]
                    if docId in checkedDocumentIds:
                        continue
                    relDocBrws = plmDocObject.browse(docId)
                    compBrws = False
                    for compBrwsRes in relDocBrws.linkedcomponents:
                        compBrws = compBrwsRes
                        break
                    docCheckCreate(relDocBrws, compBrws)
                    checkedDocumentIds.append(docId)

        #self.getAllAvailableTypes()   # Setup available types
        compIds = self.getBomCompIds()
        recursionDocuments(self.component_id.linkeddocuments)     # Check / Create ROOT structure
        for compBrws in objProduct.browse(compIds):                         # Check / Create BOM structure
            recursionDocuments(compBrws.linkeddocuments)

        self.export_2d = export_2d
        self.export_3d = export_3d
        self.export_other = export_other
        self.export_pdf = export_pdf
        return self.returnWizard()

    def returnWizard(self):
        return {'name': _('Pack and Go'),
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'pack.and_go',
                'target': 'new',
                'res_id': self.ids[0],
                'type': 'ir.actions.act_window',
                'domain': "[]"}

    def clear2d(self):
        self.write({'export_2d': [(5, 0, 0)]})
        return self.returnWizard()

    def clear3d(self):
        self.write({'export_3d': [(5, 0, 0)]})
        return self.returnWizard()

    def clearpdf(self):
        self.write({'export_pdf': [(5, 0, 0)]})
        return self.returnWizard()

    def clearother(self):
        self.write({'export_other': [(5, 0, 0)]})
        return self.returnWizard()

    def clearAll(self):
        '''
            Clear all pack and go views
        '''
        packAndGoViewObj = self.env['pack_and_go_view']
        objBrwsList = packAndGoViewObj.search([])
        objBrwsList.unlink()
        packList = self.search([('id', '!=', self.id)])
        packList.sudo().unlink()

    def getAllAvailableTypes(self):
        '''
            Read from flask server and create all needed extensions
        '''
        try:
            typesObj = self.env['pack_and_go_types']

            def checkCreateType(typeStr):
                res = typesObj.search([('name', '=', typeStr)])
                if not res:
                    typesObj.create({'name': typeStr})
            # Read from flask server
            paramObj = self.env['ir.config_parameter']
            serverAddress = paramObj._get_param('plm_convetion_server')
            if serverAddress is None:
                paramObj.create({'key': 'plm_convetion_server',
                                 'value': 'my.servrer.com:5000'})
                serverAddress = 'no_host_in_odoo_parameter"plm_convetion_server"!'
            fileExtensionsRes = requests.get('http://' + serverAddress + '/odooplm/api/v1.0/getAvailableExtention')
            res = json.loads(fileExtensionsRes.content)

            # Create all extensions
            for fileExtension, tupleConversion in res.items():
                checkCreateType(fileExtension)
                for ext in tupleConversion[-1]:
                    checkCreateType(ext)
            self.convertion_server_available = True
            return res
        except Exception as ex:
            logging.error('Error during call server to get available types: %r' % (ex))
            return {}

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
        compIds = []
        def recursion(bomBrwsList):
            for bomBrws in bomBrwsList:
                for bomLineBrws in bomBrws.bom_line_ids:
                    prodId = bomLineBrws.product_id.id
                    if prodId in compIds:
                        continue
                    compIds.append(prodId)
                    prodTmplBrws = bomLineBrws.product_id.product_tmpl_id
                    bomBrwsList = self.getBomFromTemplate(prodTmplBrws)
                    recursion(bomBrwsList)
        compIds.append(self.component_id.id)
        startingBom = self.getBomFromTemplate(self.component_id.product_tmpl_id)
        if startingBom:
            recursion(startingBom)    
        return compIds

    def checkPlmConvertionInstalled(self):
        domain = [('state', 'in', ['installed', 'to upgrade', 'to remove']), ('name', '=', 'plm_automated_convertion')]
        apps = self.env['ir.module.module'].sudo().search_read(domain, ['name'])
        if apps:
            return True
        return False

    def export2D(self, convertionModuleInstalled, outZipFile):
        for lineBrws in self.export_2d:
            if lineBrws.available_types and convertionModuleInstalled:
                exportConverted(lineBrws.document_id, lineBrws.available_types)
            else:
                self.exportSingle(lineBrws.document_id, outZipFile)

    def export3D(self, convertionModuleInstalled, outZipFile):
        for lineBrws in self.export_3d:
            if lineBrws.available_types and convertionModuleInstalled:
                exportConverted(lineBrws.document_id, lineBrws.available_types)
            else:
                self.exportSingle(lineBrws.document_id, outZipFile)

    def getPDF(self, docBws):
        report_model = self.env['report.plm.ir_attachment_pdf']
        content, _type = report_model._render_qweb_pdf(docBws)
        return content

    def exportPdf(self, outZipFile):
        for lineBrws in self.export_pdf:
            docBws = lineBrws.document_id
            outFilePath = os.path.join(outZipFile, docBws.name + '.' + 'pdf')
            if docBws.printout:
                with open(outFilePath, 'wb') as fileObj:
                    fileObj.write(self.getPDF(docBws))

    def exportOther(self, outZipFile):
        for lineBrws in self.export_other:
            self.exportSingle(lineBrws.document_id, outZipFile)

    def exportSingle(self, docBws, outZipFile):
        fromFile = docBws._full_path(docBws.store_fname)
        if os.path.exists(fromFile):
            outFilePath = os.path.join(outZipFile, docBws.name)
            shutil.copyfile(fromFile, outFilePath)
        else:
            logging.error('Unable to export file from document ID %r. File %r does not exists.' % (docBws.id, fromFile))

    def action_export_zip(self):
        """
            action to import the data
        """
        def checkCreateFolder(path):
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path)

        convertionModuleInstalled = self.checkPlmConvertionInstalled()
        tmpDir = tempfile.gettempdir()
        export_zip_folder = os.path.join(tmpDir, 'export_zip')
        checkCreateFolder(export_zip_folder)
        outZipFile = os.path.join(export_zip_folder, self.component_id.engineering_code)
        checkCreateFolder(outZipFile)

        def exportConverted(docBws, extentionBrws):
            relStr = self.env['ir.config_parameter']._get_param('extension_integration_rel')
            try:
                rel = eval(str(relStr).lower())
            except Exception as ex:
                logging.error('Unable to get extension_integration_rel parameter. EX: %r' % (ex))
                rel = {}
            integration = rel.get(str(self.getFileExtension(docBws)).lower(), '')
            convertObj = self.env['plm.convert']
            filePath = convertObj.getFileConverted(docBws, integration, extentionBrws.name)
            if not os.path.exists(filePath):
                logging.error('Unable to convert correctly file %r, does not exists' % (filePath))
                return
            outFilePath = os.path.join(outZipFile, os.path.basename(filePath))
            shutil.copyfile(filePath, outFilePath)

        self.export2D(convertionModuleInstalled, outZipFile)
        self.export3D(convertionModuleInstalled, outZipFile)
        self.exportPdf(outZipFile)
        self.exportOther(outZipFile)

        # Make archive, upload it and clean
        outZipFile2 = shutil.make_archive(outZipFile, 'zip', outZipFile)
        with open(outZipFile2, 'rb') as f:
            fileContent = f.read()
            if fileContent:
                self.datas = base64.encodebytes(fileContent)
        try:
            shutil.rmtree(outZipFile)
        except Exception as ex:
            logging.error("Unable to delete file from export function %r %r" % (outZipFile, str(ex)))
        fileName = os.path.basename(outZipFile2)
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

    def getFileExtension(self, docBrws):
        fileExtension = ''
        datas_fname = docBrws.name
        if datas_fname:
            fileExtension = '.' + datas_fname.split('.')[-1]
        return fileExtension

    def forceTypes3d(self):
        if not self.force_types_3d:
            raise UserError(_('You have to select a force type before clicking.'))
        forceType = self.force_types_3d.name
        for line in self.export_3d:
            typesObj = self.env['pack_and_go_types']
            res = typesObj.search([('name', '=', forceType)])
            if res:
                line.available_types = res.ids[0]
        return self.returnWizard()

    def forceTypes2d(self):
        if not self.force_types_2d:
            raise UserError(_('You have to select a force type before clicking.'))
        forceType = self.force_types_2d.name
        for line in self.export_2d:
            typesObj = self.env['pack_and_go_types']
            res = typesObj.search([('name', '=', forceType)])
            if res:
                line.available_types = res.ids[0]
        return self.returnWizard()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
