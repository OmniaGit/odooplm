# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
Created on 25 Aug 2016
@author: Daniel Smerghetto
"""
from distutils.command.config import config

from odoo import api, models
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUSES


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        conditional_status = RELEASED_STATUSES.copy()
        config_param = self.env["ir.config_parameter"].sudo()
        conditional_status.extend(
            config_param.get_param("sales_only_latest_params", "").split(",")
        )
        if self.env.context.get("sale_latest"):
            args += [
                "|",
                ("engineering_code", "=", False),
                ("engineering_state", "in", conditional_status),
            ]

        return super(ProductProduct, self).name_search(
            name=name, args=args, operator=operator, limit=limit
        )
