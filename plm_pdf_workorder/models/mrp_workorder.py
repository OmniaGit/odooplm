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
"""
Created on Mar 30, 2016

@author: Daniel Smerghetto
"""
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
import logging
import base64

    
class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    view_plm_pdf = fields.Boolean(_('Switch PDF'))
    plm_pdf = fields.Binary(_('Plm PDF'))
    use_plm_pdf = fields.Boolean(related='operation_id.use_plm_pdf')

    def action_switch_pdf(self):
        for workorder_id in self:
            workorder_id.view_plm_pdf = not workorder_id.view_plm_pdf
            if workorder_id.operation_id.use_plm_pdf:# and not workorder_id.plm_pdf:
                workorder_id.plm_pdf = base64.b64encode(self.getPDF(workorder_id))

    @api.model
    def create(self, vals):
        ret = super(MrpWorkorder, self).create(vals)
        if ret.operation_id.use_plm_pdf:
            ret.plm_pdf = base64.b64encode(self.getPDF(ret))
        return ret

    def getPDF(self, workorder_id):
        report_model = self.env['report.plm.product_production_one_pdf_latest']
        return report_model._render_qweb_pdf(workorder_id.product_id, checkState=True)
