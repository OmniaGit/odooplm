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


class TemplateConsumptionPlan(models.Model):
    _name = "template.consumption.plan"
    _description = "Template Comsumption Plan"
    _rec_name = 'name'

    name = fields.Char(string="Name")
    time_span = fields.Float(string="Hours")
    consumption_state_id = fields.Many2one(string="Consumption_state_id", comodel_name="consumption.state")
    product_template_ids = fields.Many2many(
        comodel_name="product.template", string="Product Templates"
    )
    product_ids = fields.Many2many(comodel_name="product.product", string="Products")
