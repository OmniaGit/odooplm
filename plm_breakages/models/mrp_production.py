# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2020 OmniaSolutions (<https://omniasolutions.website>). All Rights Reserved
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
# Leonardo Cazziolati
# leonardo.cazziolati@omniasolutions.eu
# 23-06-2020

from odoo import _, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    breakages_count = fields.Integer(
        "# Breakages", compute="_compute_breakages_count", compute_sudo=False
    )

    def get_brackege_ids_count(self):
        product_product_out = self.env["product.product"]
        product_id = self.product_id
        product_product_out += product_id
        count_out = self.env["plm.breakages"].search_count(
            [("product_id", "=", product_id.id)]
        )
        for row in self.move_raw_ids:
            product_id = row.product_id
            count_out += self.env["plm.breakages"].search_count(
                [("product_id", "=", product_id.id)]
            )
            product_product_out += product_id
        return count_out, product_product_out

    def open_breakages(self):
        _count, product_product_ids = self.get_brackege_ids_count()
        return {
            "name": _("Products"),
            "res_model": "plm.breakages",
            "view_type": "form",
            "view_mode": "list,form,pivot",
            "type": "ir.actions.act_window",
            "domain": [("product_id", "=", product_product_ids.ids)],
        }

    def _compute_breakages_count(self):
        for mrp_production in self:
            count, _ids = mrp_production.get_brackege_ids_count()
            mrp_production.breakages_count = count
