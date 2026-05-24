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
from odoo import _, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    breakages_count = fields.Integer(
        "# Breakages", compute="_compute_breakages_count", compute_sudo=False
    )

    def _get_bom_product_ids(self):
        """Return IDs of self plus all components found in related BOMs."""
        boms = self.env["mrp.bom"].search([("product_id", "in", self.ids)])
        product_ids = set(self.ids)
        for bom in boms:
            product_ids.update(bom.bom_line_ids.mapped("product_id").ids)
        return list(product_ids)

    def open_breakages(self):
        product_ids = self._get_bom_product_ids()
        return {
            "name": _("Products"),
            "res_model": "plm.breakages",
            "view_type": "form",
            "view_mode": "list,form",
            "type": "ir.actions.act_window",
            "domain": [("product_id", "in", product_ids)],
            "context": {"default_product_id": self.id},
        }

    def _compute_breakages_count(self):
        for product in self:
            product_ids = product._get_bom_product_ids()
            product.breakages_count = self.env["plm.breakages"].search_count(
                [("product_id", "in", product_ids)]
            )
