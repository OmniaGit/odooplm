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
from odoo import api
from odoo import _
from odoo.exceptions import UserError
import logging


class ProductCuttedParts(models.Model):
    _inherit = 'product.product'
    
    @api.onchange('is_row_material')
    def onchange_is_row_material(self):
        if self.is_row_material:
            self.row_material = False

    @api.onchange('row_material_x_length')
    def onchange_row_material_x_length(self):
        if not self.row_material_x_length or self.row_material_x_length == 0.0:
            raise UserError(_('"Raw Material x length" cannot have zero value.'))

    @api.onchange('row_material_y_length')
    def onchange_row_material_y_length(self):
        if not self.row_material_y_length or self.row_material_y_length == 0.0:
            raise UserError(_('"Raw Material y length" cannot have zero value.'))
