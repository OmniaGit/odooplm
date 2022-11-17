##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
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

"""
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
import logging
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging

REPORT_TEMPLATE_VALS = {'plm.product_pdf':{'level': -1, 'checkState': False,'latest':False,},
                        'plm.one_product_pdf':{'level':1, 'checkState':False,'latest':False,},
                        'plm.one_product_pdf_latest':{'level':1, 'checkState':False,'latest':True,},
                        'plm.all_product_pdf':{'level':9999999999, 'checkState':False,'latest':False,},
                        'plm.product_production_pdf_latest':{'level':0, 'checkState':True,'latest':True,},
                        'plm.product_production_one_pdf_latest':{'level':1, 'checkState':True,'latest':True,},
                        'plm.product_production_all_pdf_latest':{'level':9999999999, 'checkState':True,'latest':True,},
                        'plm.ir_attachment_pdf':{'level':0, 'checkState':False,'latest':False,}
                        }

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None):
        self_sudo = self.sudo()
        report_name = self_sudo.report_name
        plm_report = REPORT_TEMPLATE_VALS.get(report_name)
        if  plm_report:
            report_name = 'report.' + report_name
            report_obj = self.env[report_name]
            prod_ids = self.env[self_sudo.model].browse(res_ids)
            if self_sudo.model=='ir.attachment':
                return report_obj._render_qweb_pdf(res_ids=prod_ids)
            return report_obj._render_qweb_pdf(res_ids=prod_ids,
                                               level=plm_report.get("level",-1),
                                               checkState=plm_report.get('checkState', False),
                                               latest=plm_report.get('latest',False))

        return super(IrActionsReport, self)._render_qweb_pdf(res_ids, data)

