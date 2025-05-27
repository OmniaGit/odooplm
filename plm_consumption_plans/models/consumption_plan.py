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
from odoo import models, fields


class ConsumptionPlan(models.Model):
    _name = "consumption.plan"
    _description = "Consumption Plan"

    bom_line_id = fields.Many2one("mrp.bom.line", string="BoM Line")
    name = fields.Char(string="Name")
    time_span = fields.Float(string="Hours")
    state = fields.Selection(
        selection=[("mandatory", "Mandatory"), ("recommended", "Recommended")],
        string="State",
    )
    product_template_id = fields.Many2one(
        comodel_name="product.template", string="Product Template"
    )
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
