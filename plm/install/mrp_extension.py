# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
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
Created on May 18, 2016

@author: Daniel Smerghetto
'''
from openerp.osv import osv


class MrpProductionExtension(osv.osv):
    _name = 'mrp.production'
    _inherit = 'mrp.production'
    
    def product_id_change(self, cr, uid, ids, product_id, product_qty=0, context=None):
        """ Finds UoM of changed product.
        @param product_id: Id of changed product.
        @return: Dictionary of values.
        """
        result = super(MrpProductionExtension, self).product_id_change(cr, uid, ids, product_id, product_qty, context)
        outValues = result.get('value', {})
        bom_id = outValues.get('bom_id', False)
        if bom_id:
            bomBrws = self.pool.get('mrp.bom').browse(cr, uid, bom_id, context)
            if bomBrws.type == 'ebom':
                return {'value': {
                    'product_uom': False,
                    'bom_id': False,
                    'routing_id': False,
                    'product_uos_qty': 0,
                    'product_uos': False
                }}
        return result

MrpProductionExtension()
