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
import base64
import logging

from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _

_logger = logging.getLogger(__name__)

#
#  ************************** SPARE REPORTS *****************
#


class plm_spareChoseLanguage(models.TransientModel):
    _name = "plm.sparechoselanguage"
    _description = "Module for extending the functionality of printing spare_bom reports in a multi language environment"

    def getInstalledLanguage(self):
        """
            get installed language
        """
        out = []
        modobj = self.env['res.lang']
        for objBrowse in modobj.search([]):
            out.append((objBrowse.code, objBrowse.name))
        return out

    def get_report_name(self,brwProduct, lang):
        return brwProduct.name + "_" + lang + "_manual.pdf"
        
    def print_report(self):
        self.ensure_one()
        lang = self.lang
        if lang:
            modobj = self.env['ir.module.module']
            mids = modobj.search([('state', '=', 'installed')])
            if not mids:
                raise UserError("Language not Installed")
            reportName = 'report.plm_spare.pdf_all' #'plm_spare.report_product_product_spare_parts_pdf'
            if self.onelevel:
                reportName = 'report.plm_spare.pdf_one' #'plm_spare.report_product_product_spare_parts_pdf_one'
            productProductId = self.env.context.get('active_id')
            newContext = self.env.context.copy()
            newContext['lang'] = lang
            newContext['force_report_rendering']=True
            # stream, fileExtention = self.env.ref(reportName).sudo().with_context(newContext)._render_qweb_pdf(reportName,
            #                                                                                                   productProductId)

            #report_context =  self.env.ref(reportName).sudo().with_context(newContext)
            #report_context._render_qweb_pdf_prepare_streams(reportName, data={'report_type': 'pdf'}, res_ids=productProductId)
            #self.datas = base64.encodestring(stream)
            
            tProductProduct = self.env['product.product']
            brwProduct = tProductProduct.browse(productProductId)
            report_context = self.env[reportName].sudo().with_context(newContext)
            stream = report_context._create_spare_pdf(brwProduct)
            self.datas =  base64.encodebytes(stream)
            fileName = brwProduct.name + "_" + lang + "_manual.pdf"
            fileName = self.get_report_name(brwProduct, lang)
            self.datas_name = fileName
            return {'context': self.env.context,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': plm_spareChoseLanguage._name,
                    'res_id': self.id,
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    }
        UserError(_("Select a language"))

    lang = fields.Selection(getInstalledLanguage,
                            'Language',
                            required=True)

    onelevel = fields.Boolean('One Level',
                              help="If you check this box, the report will be made in one level")

    datas = fields.Binary("Download",
                          readonly=True)

    datas_name = fields.Char('Download file name ',
                             size=255,
                             readonly=True)

    _defaults = {
        'onelevel': False
    }
#
#  ************************** BOM REPORTS *****************
#


AVAILABLE_REPORT = [("plm.report_plm_bom_structure_all", "BOM All Levels"),
                    ("plm.report_plm_bom_structure_one", "BOM One Level"),
                    ("plm.report_plm_bom_structure_all_sum", "BOM All Levels Summarized"),
                    ("plm.report_plm_bom_structure_one_sum", "BOM One Level Summarized"),
                    ("plm.report_plm_bom_structure_leaves", "BOM Only Leaves Summarized"),
                    ("plm.report_plm_bom_structure_flat", "BOM All Flat Summarized")]


class plm_bomChoseLanguage(models.TransientModel):
    _name = "plm.bomchoselanguage"
    _description = "Module for extending the functionality of printing bom reports in a multi language environment"

    def getInstalledLanguage(self):
        """
            get installed language
        """
        out = []
        modobj = self.env['res.lang']
        for objBrowse in modobj.search([]):
            out.append((objBrowse.code, objBrowse.name))
        return out
    
    def get_report_name(self,brwProduct, lang, fileExtention):
        return brwProduct.product_tmpl_id.name + "_" + lang + "_bom." + fileExtention
    
    def print_report(self):
        self.ensure_one()
        lang = self.lang
        if lang:
            modobj = self.env['ir.module.module']
            mids = modobj.search([('state', '=', 'installed')])
            if not mids:
                raise UserError("Language not Installed")
            reportName = self.bom_type
            newContext = self.env.context.copy()    # Used to update and generate pdf
            newContext['lang'] = lang
            newContext['force_report_rendering']=True
            bomId = self.env.context.get('active_id')
            stream, fileExtention = self.env.ref(reportName).sudo().with_context(newContext)._render_qweb_pdf(res_ids=bomId)
            self.datas = base64.b64encode(stream)
            tMrpBom = self.env['mrp.bom']
            brwProduct = tMrpBom.browse(bomId)
            fileName = self.get_report_name(brwProduct, lang, fileExtention)
            self.datas_name = fileName
            return {'context': self.env.context,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': plm_bomChoseLanguage._name,
                    'res_id': self.id,
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    }
        raise UserError(_("Select a language"))

    lang = fields.Selection(getInstalledLanguage,
                            _('Language'),
                            required=True)

    bom_type = fields.Selection(AVAILABLE_REPORT,
                                _('Bom Report Type'),
                                required=True,
                                help=_("Chose the Bom report you would like to print"))

    datas = fields.Binary(_("Download"),
                          readonly=True)

    datas_name = fields.Char(_('Download file name '),
                             size=255,
                             readonly=True)

    _defaults = {
        'bom_type': False
    }
