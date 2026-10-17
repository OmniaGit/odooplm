# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2026 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
from odoo import api, fields, models


def normalize_extension(value):
    """'STEP', 'step' and '.Step' are all '.step'."""
    value = (value or "").strip().lower()
    if value and not value.startswith("."):
        value = "." + value
    return value


class PackGoExtension(models.Model):
    _name = "plm.pack.go.extension"
    _description = "Pack and Go file extension"
    _order = "name"

    name = fields.Char("Extension", required=True, help="File extension, e.g. .step")
    color = fields.Integer("Color")

    _name_uniq = models.Constraint(
        "unique(name)",
        "The extension has to be unique!",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "name" in vals:
                vals["name"] = normalize_extension(vals["name"])
        return super().create(vals_list)

    def write(self, vals):
        if "name" in vals:
            vals["name"] = normalize_extension(vals["name"])
        return super().write(vals)
