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
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    template_consumption_plan_ids = fields.Many2many(
        comodel_name="template.consumption.plan",
        string="Consumption Plans",
        compute="_compute_template_consumption_plan_ids",
        readonly=True
    )

    def _compute_template_consumption_plan_ids(self):
        for product in self:
            plans = self.env['template.consumption.plan'].search([('product_ids', 'in', product.id)])
            product.template_consumption_plan_ids = plans

    def act_get_consumption_plan_report(self):
        self.ensure_one()
        return self.env.ref('plm_consumption_plans.report_action_consumption_plan_product_variant').report_action(self)
