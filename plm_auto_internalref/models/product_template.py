# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging

from odoo import api, fields, models


class ProductTemplateExtension(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    auto_default_code = fields.Boolean(
        string="Automatic Internal Reference",
        default=True,
        help="Set: the internal reference is computed from the engineering code and"
        " revision, and cannot be edited.\n"
        "Unset: the internal reference is edited by hand and no longer computed.",
    )

    @api.model_create_multi
    def create(self, vals):
        obj_pp = self.env["product.product"]
        for val_dict in vals:
            if not val_dict.get("auto_default_code", True):
                continue
            new_default_code = obj_pp.compute_default_code(val_dict)
            if new_default_code:
                logging.info(f"OdooPLM: Default Code set to {new_default_code}")
                val_dict["default_code"] = new_default_code
        return super().create(vals)

    def write(self, vals):
        # Each template gets its own internal reference: write separately only the
        # templates whose reference changes, all the others together with vals
        res = True
        to_compute, others = self.env["product.product"]._split_auto_default_code(
            self, vals
        )
        for product_template_id, new_default_code in to_compute:
            logging.info(f"OdooPLM: Default Code set to {new_default_code}")
            res = (
                super(ProductTemplateExtension, product_template_id).write(
                    dict(vals, default_code=new_default_code)
                )
                and res
            )
        if others:
            res = super(ProductTemplateExtension, others).write(vals) and res
        return res
