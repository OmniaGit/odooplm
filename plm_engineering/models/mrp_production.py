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
Created on 31 Aug 2016

@author: Daniel Smerghetto
"""

from odoo import models
from odoo import api


class MrpProductionExtension(models.Model):
    _name = 'mrp.production'
    _inherit = 'mrp.production'

    def product_id_change(self, product_id, product_qty=0):
        """ Finds UoM of changed product.
        @param product_id: Id of changed product.
        @param product_qty:
        @return: Dictionary of values.
        """
        result = super(MrpProductionExtension, self).product_id_change(product_id, product_qty)
        out_values = result.get('value', {})
        bom_id = out_values.get('bom_id', False)
        if bom_id:
            bom_brws = self.env['mrp.bom'].browse(bom_id)
            if bom_brws.type == 'ebom':
                return {'value': {
                    'product_uom_id': False,
                    'bom_id': False,
                    'routing_id': False,
                    'product_uos_qty': 0,
                    'product_uos': False
                }}
        return result
