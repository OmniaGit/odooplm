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
Created on May 25, 2016

@author: Daniel Smerghetto
"""

from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging

_logger = logging.getLogger(__name__)


class PlmComponent(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    automatic_compute_selection = fields.Selection(
        [('use_net', _('Use Net Weight')),
         ('use_cad', _('Use CAD Weight')),
         ('use_normal_bom', _('Use Normal Bom'))],
        _('Weight compute mode'),
        default='use_net',
        help=_(
            """Set "Use Net Weight" to use only gross weight. Set "Use CAD Weight" to use CAD weight + Additional Weight as gross weight. Set "Use Normal Bom" to use NBOM Weight Computed + Additional weight as gross weight.""")
    )
    weight_additional = fields.Float(_('Additional Weight'), digits='Stock Weight', default=0)
    weight_cad = fields.Float(_('CAD Weight'), readonly=True, digits='Stock Weight', default=0)
    weight_n_bom_computed = fields.Float(_('NBOM Weight Computed'),
                                         compute="compute_bom_weight",
                                         readonly=True,
                                         digits='Stock Weight', default=0)

    @api.model
    def create(self, vals):
        """
            Creating a product weight is set equal to weight_net and vice-versa
        """
        if 'automatic_compute_selection' in vals:
            if vals['automatic_compute_selection']=='use_cad':
                vals['weight'] = vals.get('weight_cad', 0) + vals.get('weight_additional')
            elif vals['automatic_compute_selection']=='use_normal_bom':
                vals['weight'] = vals.get('weight_additional')
        return super(PlmComponent, self).create(vals)

    @property
    def weight_allowed_state(self):
        return  ['draft','confirmed']

    def write(self, vals):
        for product_product_id in self:
            if product_product_id.state not in self.weight_allowed_state and not self.env.context.get('plm_force_weight',False):
                if 'weight' in vals:
                    del vals['weight']
                    logging.info("Modification in status %s not allowed for the weight" % product_product_id.state)
            weight_additional = product_product_id.weight_additional
            if 'weight_additional' in vals:
                weight_additional = vals['weight_additional']
            if product_product_id.automatic_compute_selection == 'use_cad':
                weight_cad = product_product_id.weight_cad
                if 'weight_cad' in vals:
                    weight_cad = vals['weight_cad']
                vals['weight'] = weight_cad + weight_additional
            elif product_product_id.automatic_compute_selection == 'use_normal_bom':
                vals['weight'] = product_product_id.weight_additional + product_product_id.weight_n_bom_computed
        res= super(PlmComponent,self).write(vals)
        for product_product_id in self:
            product_product_id.fix_parent()
        return res
        
    def fix_parent(self):
        for product_product_id in self:
            bom_id = product_product_id.getParentBom()
            if bom_id:
                bom_id.product_tmpl_id.product_variant_id.on_change_automatic_compute()   

    @api.onchange('automatic_compute_selection','weight_cad','weight_additional','weight_n_bom_computed')
    def on_change_automatic_compute(self):
        """
            Compute weight due to selection choice
        """
        if self.automatic_compute_selection == 'use_cad':
            self.weight = self.weight_cad + self.weight_additional
        elif self.automatic_compute_selection == 'use_normal_bom':
            self.compute_bom_weight()
            self.weight = self.weight_additional + self.weight_n_bom_computed
        
    def compute_bom_weight(self):
        bom_obj = self.env['mrp.bom']
        for product_product_id in self:
            product_product_id.weight_n_bom_computed = 0.0
            product_tmpl_id = product_product_id.product_tmpl_id._origin.id
            for bom_id in bom_obj.search([('type', '=', 'normal'), ('product_tmpl_id', '=', product_tmpl_id)]):
                product_product_id.weight_n_bom_computed = bom_id.get_bom_child_weight()

        
    def compute_bom_weight_action(self):
        """
            Function called form xml action to compute and set weight for all selected products and boms
        """
        for prod_brws in self:
            prod_brws.on_change_automatic_compute()
