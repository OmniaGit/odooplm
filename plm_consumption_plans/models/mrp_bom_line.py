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
from odoo import (models, 
                  fields, 
                  api)


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    template_consumption_plan_ids = fields.Many2many(
        comodel_name="template.consumption.plan",
        string="Consumption Plans",
    )

    @api.model_create_multi
    def create(self, vals):
        line_ids = super().create(vals)
        for bom_line_id in line_ids:
            bom_product = bom_line_id.product_id
            if not bom_product.is_independent_consumption_plan and bom_product.template_consumption_plan_ids:
                bom_line_id.template_consumption_plan_ids = [(6,0,bom_product.template_consumption_plan_ids.ids)]
        return line_ids
