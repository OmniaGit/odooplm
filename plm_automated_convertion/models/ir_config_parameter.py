# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import  models, api

class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(rec.key == 'Cad Excange Cli' for rec in records):
            self.env['plm.convert.format'].sudo()._update_cad_ex_availability()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'value' in vals and any(record.key == 'Cad Excange Cli' for record in self):
            self.env['plm.convert.format'].sudo()._update_cad_ex_availability()
        return res
