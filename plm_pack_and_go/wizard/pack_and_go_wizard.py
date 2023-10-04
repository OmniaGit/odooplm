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

    component_id = fields.Many2one('product.template', _('Component'))
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
        obj_id = self._context.get('active_id')
        obj_model = self._context.get('active_model')
        if obj_id:
            if obj_model == 'product.product':
                return self.env[obj_model].browse(obj_id).product_tmpl_id.id
            elif obj_model == 'product.template':
                return obj_id
        return False

    component_id = fields.Many2one('product.template',
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
    create_subfolder_by_category = fields.Boolean(_("Create subfolder by category"),help="""
    Create inside the zip a folder structure that is equal to the product category assing to each product
    """)
    bom_computation = fields.Selection([('ONLY_PRODUCT', 'Selected product'),
                                        ('FIRST_LEVEL','First Level'),
                                        ('ALL_LEVEL','All Level'),
                                        ('LEAF','Leaf')],
                                       _("Bom computation mode"),
                                       default='ALL_LEVEL')
    
    file_name_computation = fields.Selection([('FILE_NAME', 'File name'),
                                  ('FILE_NAME_REV', 'File name and revision'),
                                  ('PRODUCT_ENGINEERING_CODE','Product engineering Code'),
                                  ('PRODUCT_ENGINEERING_REV','Product engineering name and revision'),
                                  ('PRODUCT_ENGINEERING_DESCCRIPRION','Product engineering name and description'),
                                  ('PRODUCT_ENGINEERING_REV_DESCCRIPRION','Product engineering name revision and descriprion'),
                                  ('INTERNAL_REFERENCE','Product internal reference'),
                                  ('INTERNAL_REFERENCE_DESCRIPTION','Product internal reference and description')],
                                  _("File name computation"),
                                  default='FILE_NAME',
                                  help="""
                                  File name inside zip folder
                                  * File name -> <ir_attachment.name>.exte 
                                  * File name and revision -> <ir_attachment.name>_<ir_attachment.engineering_revision>.exte
                                  * Product engineering Code -> <product_product.engineering_code>.exte
                                  * Product engineering name and revision -> <product_product.engineering_code>_<eproduct_product.engineering_revision>.exte
                                  * Product engineering name description -> <product_product.engineering_code>_<product_product.name>.exte
                                  * Product engineering name revision and descriprion - > <product_product.engineering_code>_<product_product.engineering_revision>_<product_product.name>.exte
                                  * Product internal reference' - > <product_product.default_code>.exte
                                  * Product internal reference and description' - > <product_product.default_code>_<product_product.name>.exte
                                  REMARK: This function only work for the non CAD native files [es. it work for (pdf,dxf,stp)]
                                      Native file must keep the original name in order to be reopened without any problem
                                  """)
    bom_version = fields.Selection([('ONLY_RELEASED', _('Released')),
                                    ('LATEST',_('Latest'))],
                                    string=_("Product-Document version"),
                                    default='LATEST',
                                    help="""Chose the status of the document that you would like to extract""")
    
    show_create_zip = fields.Boolean("Service field to show crete zip button",
                                     compute="compute_show_create_zip")
    def compute_show_create_zip(self):
        for item in self:
            item.show_create_zip=False
            if item.export_3d:
                item.show_create_zip=True
                return
            if item.export_2d:
                item.show_create_zip=True
                return
            if item.export_pdf:
                item.show_create_zip=True
                return
            if item.export_other:
                item.show_create_zip=True
                return          
            
    def docCheckCreate(self, ir_attachment_id, product_product_id=False):
        product_template_id = False
        product_template_revision = False
        objPackView = self.env['pack_and_go_view']
        if product_product_id:
            product_template_id = product_product_id.product_tmpl_id.id
            product_template_revision = product_product_id.engineering_revision
        singleCreateDict = {'component_id': product_template_id,
                            'comp_rev': product_template_revision,
                            'doc_rev': ir_attachment_id.engineering_revision,
                            'document_id': ir_attachment_id.id,
                            'preview': ir_attachment_id.preview,
                            'available_types': False,
                            'doc_type': ir_attachment_id.document_type,
                            }
        return objPackView.create(singleCreateDict)
    
    def action_compute_attachment_bom(self):
        """
        compute the bom and get the attachment
        """
        #
        export_2d = []
        export_3d = []
        export_other = []
        export_pdf = []
        #
        self.clearAll()
        #
        computed = []
        for product_product_id, attachment_ids in self.get_attachment(self.component_id.product_variant_id).items():
            for ir_attachment_id in attachment_ids:
                if ir_attachment_id in computed:
                    continue
                computed.append(ir_attachment_id)
                newViewObj = self.docCheckCreate(ir_attachment_id, product_product_id)
                if ir_attachment_id.document_type == '2d':
                    if self.export_type in ('2dpdf','2d', '3d2d', 'all'):
                        export_2d.append(newViewObj.id)
                    if self.export_type in ('2dpdf', 'pdf', '3dpdf', 'all'):
                        cp_newViewObj = newViewObj.copy()
                        cp_newViewObj.doc_type='pdf'
                        export_pdf.append(cp_newViewObj.id)
                elif ir_attachment_id.document_type == '3d':
                    if self.export_type in ('3d', '3dpdf', '3d2d', 'all'):
                        export_3d.append(newViewObj.id)
                elif ir_attachment_id.document_type == 'other':
                    if self.export_type in ('all'):
                        export_other.append(newViewObj.id)
                else:
                    logging.error(f"Document {ir_attachment_id.name} of type {ir_attachment_id.document_type} not collexted")
                    
        #
        self.export_2d = list(set(export_2d))
        self.export_3d = list(set(export_3d))
        self.export_other = list(set(export_other))
        self.export_pdf = list(set(export_pdf))
        #
        return self.returnWizard()

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
        objProduct = self.env['product.template']
        objPackView = self.env['pack_and_go_view']
        plmDocObject = self.env['ir.attachment']

        def docCheckCreate(ir_attachment_id, product_product_id=False):
            compId = False
            compRev = False
            if product_product_id:
                compId = product_product_id.product_tmpl_id.id
                compRev = product_product_id.engineering_revision
            singleCreateDict = {'component_id': compId,
                                'comp_rev': compRev,
                                'doc_rev': ir_attachment_id.engineering_revision,
                                'document_id': ir_attachment_id.id,
                                'preview': ir_attachment_id.preview,
                                'available_types': False,
                                'doc_type': ir_attachment_id.document_type,
                                }
            if ir_attachment_id.document_type == '2d':
                if self.export_type in ('2d', '2dpdf', '3d2d', 'all'):
                    newViewObj = objPackView.create(singleCreateDict)
                    export_2d.append(newViewObj.id)
                if self.export_type in ('2dpdf', 'pdf', '3dpdf', 'all'):
                    singleCreateDict['doc_type'] = 'pdf'
                    newViewObj = objPackView.create(singleCreateDict)
                    export_pdf.append(newViewObj.id)
            elif ir_attachment_id.document_type == '3d':
                if self.export_type in ('3d', '3dpdf', '3d2d', 'all'):
                    newViewObj = objPackView.create(singleCreateDict)
                    export_3d.append(newViewObj.id)
            else:
                newViewObj = objPackView.create(singleCreateDict)
                export_other.append(newViewObj.id)

        def recursionDocuments(docBrwsList):
            for ir_attachment_id in docBrwsList:          
                res = plmDocObject.CheckAllFiles([ir_attachment_id.id, [],
                                                  False,
                                                  'localhost',
                                                  'pack_go'])   # Get all related documents to root documents
                for singleRes in res:
                    docId = singleRes[0]
                    if docId in checkedDocumentIds:
                        continue
                    relDocBrws = plmDocObject.browse(docId)
                    product_template_id = False
                    for compBrwsRes in relDocBrws.linkedcomponents:
                        product_template_id = compBrwsRes
                        break
                    docCheckCreate(relDocBrws, product_template_id)
                    checkedDocumentIds.append(docId)

        #self.getAllAvailableTypes()   # Setup available types
        compIds = self.getBomCompIds()
        recursionDocuments(self.component_id.product_variant_id.linkeddocuments)     # Check / Create ROOT structure
        for product_template_id in objProduct.browse(compIds):                         # Check / Create BOM structure
            recursionDocuments(product_template_id.product_variant_id.linkeddocuments)

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
        product_template_ids = []
        def recursion(mrp_bom_ids):
            for mrp_bom_id in mrp_bom_ids:
                for mrp_bom_line_id in mrp_bom_id.bom_line_ids:
                    product_template_id = mrp_bom_line_id.product_id.product_tmpl_id
                    if product_template_id.id in product_template_ids:
                        continue
                    product_template_ids.append(product_template_id.id)
                    child_mrp_bom_ids = self.getBomFromTemplate(product_template_id)
                    recursion(child_mrp_bom_ids)
        product_template_ids.append(self.component_id.id)
        startingBom = self.getBomFromTemplate(self.component_id)
        if startingBom:
            recursion(startingBom)    
        return product_template_ids

    def checkPlmConvertionInstalled(self):
        domain = [('state', 'in', ['installed', 'to upgrade', 'to remove']), ('name', '=', 'plm_automated_convertion')]
        apps = self.env['ir.module.module'].sudo().search_read(domain, ['name'])
        if apps:
            return True
        return False

    def export2D(self, convertionModuleInstalled, outZipFile):
        for lineBrws in self.export_2d:
            if lineBrws.available_types and convertionModuleInstalled:
                self.exportConverted(lineBrws)
            else:
                self.exportSingle(lineBrws, outZipFile)

    def export3D(self, convertionModuleInstalled, outZipFile):
        for lineBrws in self.export_3d:
            if lineBrws.available_types and convertionModuleInstalled:
                self.exportConverted(lineBrws)
            else:
                self.exportSingle(lineBrws, outZipFile)

    def getPDF(self, docBws):
        report_model = self.env['report.plm.ir_attachment_pdf']
        content, _type = report_model._render_qweb_pdf(docBws)
        return content

    def exportPdf(self, outZipFile):
        for line_brws in self.export_pdf:
            ir_attachment_id = line_brws.document_id
            out_file_path = self.computeDocName(line_brws, outZipFile)
            if ir_attachment_id.printout:
                with open(f"{out_file_path}.pdf", 'wb') as fileObj:
                    fileObj.write(self.getPDF(ir_attachment_id))

    def exportOther(self, outZipFile):
        for lineBrws in self.export_other:
            self.exportSingle(lineBrws, outZipFile)

    def getCategoryFolder(self, product_id=None):
        out='All'
        if product_id:
            out = product_id.categ_id.name
        return out

    def computeDocName(self, lineBrws, outZipFile, compute_file_name=True):
        ir_attachment_id = lineBrws.document_id
        product_id = lineBrws.component_id
        file_name = ir_attachment_id.name
        if compute_file_name:
            file_name_no_exte, exte = os.path.splitext(ir_attachment_id.name)
            if self.file_name_computation =='FILE_NAME_REV':
                file_name = f"{file_name_no_exte}_{ir_attachment_id.engineering_revision}{exte}"
            else:
                if product_id:
                    if self.file_name_computation=='PRODUCT_ENGINEERING_CODE':
                        file_name = f"{product_id.engineering_code}{exte}"
                    elif self.file_name_computation=='PRODUCT_ENGINEERING_REV':
                        file_name = f"{product_id.engineering_code}_{product_id.engineering_revision}{exte}"
                    elif self.file_name_computation=='PRODUCT_ENGINEERING_DESCCRIPRION':
                        file_name = f"{product_id.engineering_code}_{product_id.name}{exte}"
                    elif self.file_name_computation=='PRODUCT_ENGINEERING_REV_DESCCRIPRION':
                        file_name = f"{product_id.engineering_code}_{product_id.engineering_revision}_{product_id.name}{exte}"
                    elif self.file_name_computation=='INTERNAL_REFERENCE':
                        file_name = f"{product_id.default_code}{exte}"
                    elif self.file_name_computation=='INTERNAL_REFERENCE_DESCRIPTION':
                        file_name = f"{product_id.default_code}_{product_id.name}{exte}"
        if self.create_subfolder_by_category:
            category_folder = self.getCategoryFolder(product_id)
            category_folder_path = os.path.join(outZipFile, category_folder)
            if not os.path.exists(category_folder_path):
                os.makedirs(category_folder_path)
            outFilePath = os.path.join(category_folder_path, file_name)
        else:
            outFilePath = os.path.join(outZipFile, file_name)
        return outFilePath

    def exportSingle(self, lineBrws, outZipFile):
        ir_attachment_id = lineBrws.document_id
        fromFile = ir_attachment_id._full_path(ir_attachment_id.store_fname)
        outFilePath = self.computeDocName(lineBrws, outZipFile, compute_file_name=False)
        if os.path.exists(fromFile):
            shutil.copyfile(fromFile, outFilePath)
        else:
            logging.error('Unable to export file from document ID %r. File %r does not exists.' % (ir_attachment_id.id, fromFile))
    
    def exportConverted(self, line_wizard_brows):
        ir_attachment_id = line_wizard_brows.document_id
        relStr = self.env['ir.config_parameter'].sudo()._get_param('extension_integration_rel')
        try:
            rel = eval(str(relStr).lower())
        except Exception as ex:
            logging.error('Unable to get extension_integration_rel parameter. EX: %r' % (ex))
            rel = {}
        integration = rel.get(str(self.getFileExtension(ir_attachment_id)).lower(), '')
        convertObj = self.env['plm.convert']
        filePath = convertObj.getFileConverted(ir_attachment_id, integration, line_wizard_brows.available_types)
        if not os.path.exists(filePath):
            logging.error('Unable to convert correctly file %r, does not exists' % (filePath))
            return
        outFilePath = os.path.join(outZipFile, os.path.basename(filePath))
        shutil.copyfile(filePath, outFilePath)
            
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
        #
        self.export2D(convertionModuleInstalled, outZipFile)
        self.export3D(convertionModuleInstalled, outZipFile)
        self.exportPdf(outZipFile)
        self.exportOther(outZipFile)
        #
        # Make archive, upload it and clean
        #
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

                                     
    def get_version(self, obj):
        if obj._name=='product.product':
            obj=obj.product_tmpl_id
        out = None
        if self.bom_version=='ONLY_RELEASED':
            out = obj.get_released()
        elif self.bom_version=='LATEST':
            out= obj.get_latest_version()
        if obj._name=='product.template':
            if out:
                out=out.product_variant_id
        return out
    
    def get_version_list(self, objs):
        out = []
        for obj in objs:
            out.append(self.get_version(obj))

        return out
        
    def get_attachment(self,
                       product_product_id,
                       version='latest',
                       bom_type='normal'):
        """
        :product_product_id product_product object to get the attachment from
        :version ['latest','selected'
        :bom_type ['normal','engineering']
        :return: {<product_product_id>:[<ir_attachment_id>]}
        """
        out={}
        ir_attachment = self.env['ir.attachment']
        product_product_ids = self.get_version(product_product_id)
        all_attchment_collected = self.env['ir.attachment']
        bom_level = self.bom_computation
        if bom_level == 'FIRST_LEVEL':
            product_product_ids = self.env['product.product']
            ids = product_product_id._getChildrenBom(product_product_id,
                                                         level = bom_level=='FIRST_LEVEL',
                                                         bom_type =bom_type)
            for child_product_product_id in self.get_version_list(self.env['product.product'].browse(ids)):
                product_product_ids+=child_product_product_id
        elif bom_level == 'ALL_LEVEL':
            ids = product_product_id._getChildrenBom(product_product_id,
                                                         level = bom_level=='FIRST_LEVEL',
                                                         bom_type =bom_type)
            for child_product_product_id in self.get_version_list(self.env['product.product'].browse(ids)):
                product_product_ids+=child_product_product_id
        elif bom_level=='LEAF':
            product_product_ids = self.env['product.product']
            for leaf_product_id in self.get_version_list(product_product_id.getLeafBom(bom_type=bom_type)):
                product_product_ids+=leaf_product_id
        
        for product_product_id in product_product_ids:
            for ir_attachment_id in product_product_id.linkeddocuments:
                if ir_attachment_id not in all_attchment_collected:
                    all_attchment_collected+=ir_attachment_id
                    if product_product_id not in out:
                        out[product_product_id]=[ir_attachment_id]
                    else:
                        out[product_product_id].append(ir_attachment_id)
                    for ref_ir_attachment_id in ir_attachment.browse(ir_attachment.getRelatedHiTree(ir_attachment_id.id,
                                                                                                    recursion=True,
                                                                                                    getRftree=True)):
                        if ref_ir_attachment_id not in all_attchment_collected:
                            all_attchment_collected+=ref_ir_attachment_id
                        if product_product_id not in out:
                            out[product_product_id]=[ref_ir_attachment_id]
                        else:
                            out[product_product_id].append(ref_ir_attachment_id)
        return out
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
