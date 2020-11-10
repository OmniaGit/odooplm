##############################################################################
#
#    OmniaSolutions, Open Source Management Solution    
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
Created on Mar 30, 2016

@author: Daniel Smerghetto
"""
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
import logging


class ProductTemplateCuttedParts(models.Model):
    _inherit = 'product.template'
    row_material = fields.Many2one('product.product', _("Raw Material Product"))
    row_material_factor = fields.Float('Raw Material Conversion Factor')
    row_material_x_length = fields.Float(_("X Raw Material length"), default=1.0)
    row_material_y_length = fields.Float(_("Y Raw Material length"), default=1.0)
    wastage_percent = fields.Float(_("X Percent Wastage"), default=0.0)
    wastage_percent_y = fields.Float(_("Y Percent Wastage"), default=0.0)
    material_added = fields.Float(_("X Material Wastage"), default=0.0)
    material_added_y = fields.Float(_("Y Material Wastage"), default=0.0)
    is_row_material = fields.Boolean(_("Is Raw Material"))
    bom_rounding = fields.Float(_("Product Rounding"), default=0.0) # Not used, removed!!