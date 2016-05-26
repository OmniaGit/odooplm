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
import openerp

from openerp.exceptions import UserError
from openerp import models, fields, api, SUPERUSER_ID, _, osv
_logger = logging.getLogger(__name__)

#
#  ************************** SPARE REPORTS *****************
#


class plm_spareChoseLanguage(osv.osv.osv_memory):
    _name = "plm.sparechoselanguage"
    _description = "Module for extending the functionality of printing spare_bom reports in a multi language environment"

    @api.v8
    def getInstalledLanguage(self):
        """
            get installed language
        """
        out = []
        modobj = self.env['res.lang']
        for objBrowse in modobj.search([]):
            out.append((objBrowse.code, objBrowse.name))
        return out

    @api.multi
    def print_report(self):
        self.ensure_one()
        lang = self.lang
        if lang:
            modobj = self.env['ir.module.module']
            mids = modobj.search([('state', '=', 'installed')])
            if not mids:
                raise UserError("Language not Installed")
            reportName = 'product.product.spare.parts.pdf'
            if self.onelevel:
                reportName = 'product.product.spare.parts.pdf.one'
            srv = openerp.report.interface.report_int._reports['report.' + reportName]
            productProductId = self.env.context.get('active_id')
            newContext = self.env.context.copy()
            newContext['lang'] = lang
            stream, fileExtention = srv.create(self.env.cr, self.env.uid, [productProductId, ], {'raise_report_warning': False}, context=newContext)
            self.datas = base64.encodestring(stream)
            tProductProduct = self.env['product.product']
            brwProduct = tProductProduct.browse(productProductId)
            fileName = brwProduct.name + "_" + lang + "_manual." + fileExtention
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
plm_spareChoseLanguage()


#
#  ************************** BOM REPORTS *****************
#
AVAILABLE_REPORT = [("plm.bom_structure_all", "BOM All Levels"),
                    ("plm.bom_structure_one", "BOM One Level"),
                    ("plm.bom_structure_all_sum", "BOM All Levels Summarized"),
                    ("plm.bom_structure_one_sum", "BOM One Level Summarized"),
                    ("plm.bom_structure_leaves", "BOM Only Leaves Summarized"),
                    ("plm.bom_structure_flat", "BOM All Flat Summarized"),
                    ]


class plm_bomChoseLanguage(osv.osv.osv_memory):
    _name = "plm.bomchoselanguage"
    _description = "Module for extending the functionality of printing bom reports in a multi language environment"

    @api.v8
    def getInstalledLanguage(self):
        """
            get installed language
        """
        out = []
        modobj = self.env['res.lang']
        for objBrowse in modobj.search([]):
            out.append((objBrowse.code, objBrowse.name))
        return out

    @api.multi
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
            template_ids = self.env['ir.ui.view'].search([('name', '=', reportName)])
            stream, fileExtention = self.env['report'].with_context(newContext).get_pdf(template_ids, reportName), 'pdf'
            bomId = self.env.context.get('active_id')
            self.datas = base64.encodestring(stream)
            tMrpBom = self.env['mrp.bom']
            brwProduct = tMrpBom.browse(bomId)
            fileName = brwProduct.product_tmpl_id.name + "_" + lang + "_bom." + fileExtention
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
        UserError(_("Select a language"))

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
plm_bomChoseLanguage()
