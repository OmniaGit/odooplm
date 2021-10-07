##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2020 OmniaSolutions (<https://omniasolutions.website>). All Rights Reserved
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
# Leonardo Cazziolati
# leonardo.cazziolati@omniasolutions.eu
# 23-06-2020

from odoo import models
from odoo import fields
from odoo import api
from odoo import _

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def open_breakages(self):
        return {'name': _('Products'),
                'res_model': 'plm.breakages',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'type': 'ir.actions.act_window',
                'domain': [('product_id', '=', self.id)],
                'context': {'default_product_id': self.id}}

    breakages_count = fields.Integer('# Breakages',
        compute='_compute_breakages_count', compute_sudo=False)
    
    def _compute_breakages_count(self):
        for product in self:
            product.breakages_count = self.env['plm.breakages'].search_count([('product_id', '=', self.id)])

            