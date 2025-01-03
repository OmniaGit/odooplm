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
from odoo import _, api, fields, models


class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    use_plm_pdf = fields.Boolean(_("Use PLM PDF"))
    plm_pdf = fields.Binary(_("Plm PDF"), compute="_compute_plm_pdf_data")

    def _compute_plm_pdf_data(self):
        workorder_id = self.env["mrp.workorder"].search([
            ("operation_id", "in", self.ids)
        ], limit=1)
        for rec in self:
            if rec.use_plm_pdf:
                rec.plm_pdf = workorder_id.plm_pdf
            else:
                rec.plm_pdf = False
