# -*- encoding: utf-8 -*-
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

'''
Created on Mar 30, 2016

@author: Daniel Smerghetto
'''
import logging
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
from openerp.exceptions import UserError
_logger = logging.getLogger(__name__)


class product_templateCuttedParts(models.Model):
    _inherit = 'product.template'
    row_material = fields.Many2one('product.product', _("Raw Material Product"))
    row_material_xlenght = fields.Float(_("Raw Material x lenght"), default=1.0)
    row_material_ylenght = fields.Float(_("Raw Material y lenght"), default=1.0)
    wastage_percent = fields.Float(_("Percent Wastage"), default=0.0)
    material_added = fields.Float(_("Material Wastage"), default=0.0)
    is_row_material = fields.Boolean(_("Is Row Material"))

product_templateCuttedParts()


class product_productCuttedParts(models.Model):
    _inherit = 'product.product'

    @api.onchange('is_row_material')
    def onchange_is_row_material(self):
        if self.is_row_material:
            self.row_material = False

    @api.onchange('row_material_xlenght')
    def onchange_row_material_xlenght(self):
        if not self.row_material_xlenght or self.row_material_xlenght == 0.0:
            raise UserError('"Raw Material x lenght" cannot have zero value.')

    @api.onchange('row_material_ylenght')
    def onchange_row_material_ylenght(self):
        if not self.row_material_ylenght or self.row_material_xlenght == 0.0:
            raise UserError('"Raw Material y lenght" cannot have zero value.')

#     def verifyRowMatLenght(self, vals):
#         if 'row_material_xlenght' in vals:
#             row_material_xlenght = vals.get('row_material_xlenght')
#             if not row_material_xlenght or row_material_xlenght == 0.0:
#                 raise UserError('"Raw Material x lenght" cannot have zero value.')
#         if 'row_material_ylenght' in vals:
#             row_material_ylenght = vals.get('row_material_ylenght')
#             if not row_material_ylenght or row_material_xlenght == 0.0:
#                 raise UserError('"Raw Material y lenght" cannot have zero value.')

#     @api.multi
#     def write(self, vals):
#         self.verifyRowMatLenght(vals)
#         return super(product_productCuttedParts, self).write(vals)
# 
#     @api.model
#     def create(self, vals):
#         self.verifyRowMatLenght(vals)
#         return super(product_productCuttedParts, self).create(vals)

product_productCuttedParts()
