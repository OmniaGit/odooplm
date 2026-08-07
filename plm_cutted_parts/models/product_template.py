# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
from odoo import _, fields, models


class ProductTemplateCuttedParts(models.Model):
    _inherit = "product.template"
    row_material = fields.Many2one("product.product", "Raw Material Product")
    row_material_factor = fields.Float("Raw Material Conversion Factor")
    row_material_x_length = fields.Float("X Raw Material length", default=1.0)
    row_material_y_length = fields.Float("Y Raw Material length", default=1.0)
    wastage_percent = fields.Float("X Percent Wastage")
    wastage_percent_y = fields.Float("Y Percent Wastage")
    material_added = fields.Float("X Material Wastage")
    material_added_y = fields.Float("Y Material Wastage")
    is_row_material = fields.Boolean("Is Raw Material")
