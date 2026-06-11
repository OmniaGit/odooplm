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
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    template_consumption_plan_ids = fields.Many2many(
        comodel_name="template.consumption.plan",
        string="Consumption Plans",
    )
    is_independent_consumption_plan = fields.Boolean(
        string="Independent Consumption Plan",
        help="If enabled, the BoM line has its own consumption plans and changes here won’t affect the product.",
        default=False,
        copy=False,
    )

    def act_get_consumption_plan_report(self):
        self.ensure_one()
        return self.env.ref(
            "plm_consumption_plans.report_action_consumption_plan"
        ).report_action(self)
