# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    plm_access_id = fields.Many2one(
        "plm.access",
        "PLM Access Root",
        copy=False,
        ondelete="restrict",
        help="The root PLM access node of the company: its documents live in it "
        "or in the department nodes below it.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies.filtered(lambda company: not company.plm_access_id):
            company._create_plm_access_root()
        return companies

    def _create_plm_access_root(self):
        self.ensure_one()
        self.plm_access_id = (
            self.env["plm.access"]
            .sudo()
            .create({"name": self.name, "company_id": self.id})
        )
