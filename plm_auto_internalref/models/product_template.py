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
Created on 9 Dec 2016

@author: Daniel Smerghetto
"""

import logging

from odoo import api, models


class ProductTemplateExtension(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals):
        obj_pp = self.env["product.product"]
        for val_dict in vals:
            if "engineering_code" in val_dict and val_dict["engineering_code"] != False:
                new_default_code = obj_pp.computeDefaultCode(val_dict)
                if new_default_code:
                    logging.info(
                        "OdooPLM: Default Code set to %s " % (new_default_code)
                    )
                    val_dict["default_code"] = new_default_code
        return super().create(vals)

    def write(self, vals):
        # Each template gets its own default code: write separately only the templates
        # whose code changes, all the others together with the original vals
        res = True
        unchanged = self.browse()
        for product_template_id in self:
            new_default_code = False
            if product_template_id.engineering_code:
                new_default_code = self.env["product.product"].computeDefaultCode(
                    vals, product_template_id
                )
            if not new_default_code or new_default_code == product_template_id.default_code:
                unchanged |= product_template_id
                continue
            if product_template_id.product_variant_id.default_code != new_default_code:
                product_template_id.product_variant_id.default_code = new_default_code
            res = super(ProductTemplateExtension, product_template_id).write(
                dict(vals, default_code=new_default_code)
            ) and res
        if unchanged:
            res = super(ProductTemplateExtension, unchanged).write(vals) and res
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
