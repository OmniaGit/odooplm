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

from odoo import api, fields, models


class ProductProductExtension(models.Model):
    _name = "product.product"
    _inherit = "product.product"

    auto_default_code = fields.Boolean(
        related="product_tmpl_id.auto_default_code",
        readonly=False,
    )

    @api.model_create_multi
    def create(self, vals):
        for val_dict in vals:
            auto_default_code = val_dict.get("auto_default_code")
            if auto_default_code is None:
                template_id = val_dict.get("product_tmpl_id")
                auto_default_code = (
                    self.env["product.template"].browse(template_id).auto_default_code
                    if template_id
                    else True
                )
            if not auto_default_code:
                continue
            new_default_code = self.computeDefaultCode(val_dict)
            if new_default_code:
                logging.info("OdooPLM: Default Code set to %s " % (new_default_code))
                val_dict["default_code"] = new_default_code
        return super().create(vals)

    @property
    def getDefaultCodeTemplate(self):
        return "%s_%s"

    def computeDefaultCode(self, vals={}, objBrowse=None):
        """
        Function to be overloaded for changing the internal reference computation
        :vals dict like with all the value that be updated
        :objBrowse product.product or product.template in case of write operation
        :return: the internal reference of the engineering code and revision in vals,
                 those vals does not carry taken from objBrowse; False without an
                 engineering code
        """
        engineering_code = vals.get("engineering_code")
        engineering_revision = vals.get("engineering_revision") or 0
        if objBrowse:  # suppose write operation
            if "engineering_code" not in vals:
                engineering_code = objBrowse.engineering_code
            if "engineering_revision" not in vals:
                engineering_revision = objBrowse.engineering_revision
        if not engineering_code or engineering_code == "-":
            return False
        return self.getDefaultCodeTemplate % (engineering_code, engineering_revision)

    def _split_auto_default_code(self, records, vals):
        """
        Split the records (products or templates) a write is about to change
        :return: the (record, internal reference) pairs of the records whose internal
                 reference must become the computed one, and the other records, that
                 take vals as they are. A record follows the computed internal
                 reference while its auto_default_code is set
        """
        to_compute = []
        others = records.browse()
        for record in records:
            new_default_code = False
            if vals.get("auto_default_code", record.auto_default_code):
                new_default_code = self.computeDefaultCode(vals, record)
            if (
                new_default_code
                and vals.get("default_code", record.default_code) != new_default_code
            ):
                to_compute.append((record, new_default_code))
            else:
                others |= record
        return to_compute, others

    def write(self, vals):
        res = True
        to_compute, others = self._split_auto_default_code(self, vals)
        for product, new_default_code in to_compute:
            logging.info("OdooPLM: Default Code set to %s " % (new_default_code))
            res = (
                super(ProductProductExtension, product).write(
                    dict(vals, default_code=new_default_code)
                )
                and res
            )
        if others:
            res = super(ProductProductExtension, others).write(vals) and res
        return res
