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
Created on 13 Jun 2016

@author: Daniel Smerghetto
"""

from odoo import models
from odoo import api


class MrpBomExtension(models.Model):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

    def force_compute_bom_weight(self):
        """
            Call plm bom weight calculator function
        """
        self.rebase_bom_weight()
    
    def get_bom_child_weight(self):
        self.ensure_one()
        out = 0.0
        for mrp_bom_id in self:
            for bom_line_id in mrp_bom_id.bom_line_ids: 
                out+= bom_line_id.product_id.weight  * bom_line_id.product_qty
        return out
        
        
