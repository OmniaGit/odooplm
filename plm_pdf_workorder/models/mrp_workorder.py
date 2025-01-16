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
"""
Created on Mar 30, 2016
@author: Daniel Smerghetto
"""
import base64
from odoo import _, api, fields, models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    plm_pdf = fields.Binary(_("Plm PDF"), compute="_compute_production_pdf", store=True)
    use_plm_pdf = fields.Boolean(
        related="operation_id.use_plm_pdf", string=_("Use PLM PDF")
    )
    production_doc_ids = fields.Many2many("ir.attachment",
                                          compute="_compute_production_doc_ids",
                                          store=True)

    @api.depends("product_id.linkeddocuments.is_production_doc")
    def _compute_production_doc_ids(self):
        for rec in self:
            if rec.product_id.linkeddocuments:
                rec.production_doc_ids = rec.product_id.linkeddocuments.filtered(
                    lambda doc: doc.is_production_doc == True
                )
            else:
                rec.production_doc_ids = False

    @api.model_create_multi
    def create(self, vals):
        ret = super(MrpWorkorder, self).create(vals)
        for r in ret:
            r.refresh_plm_instruction_pdf()
        return ret

    def refresh_plm_instruction_pdf(self):
        self.ensure_one()
        if self.operation_id.use_plm_pdf:
            self.plm_pdf = base64.b64encode(self.getAttachmentWorkorderPDF())

    def getAttachmentWorkorderPDF(self):
        self.ensure_one()
        report_model = self.env["report.plm.product_production_one_pdf_latest"]
        return report_model._render_qweb_pdf(self.product_id, checkState=True)

