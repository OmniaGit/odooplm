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
import odoo.addons.decimal_precision as dp
from odoo.addons.plm.models.plm_mixin import START_STATUS
from odoo.addons.plm.models.plm_mixin import CONFIRMED_STATUS
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUS
from odoo.addons.plm.models.plm_mixin import UNDER_MODIFY_STATUS
from odoo.addons.plm.models.plm_mixin import OBSOLATED_STATUS
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
            """Set "Use Net Weight" to use only gross weight. \n
               Set "Use CAD Weight" to use CAD weight + Additional Weight as gross weight. \n
               Set "Use Normal Bom" to use NBOM Weight Computed + Additional weight as gross weight.""")
    )
    weight_additional = fields.Float(_('Additional Weight'), digits='Stock Weight', default=0)
    weight_cad = fields.Float(_('CAD Weight'), readonly=True, digits='Stock Weight', default=0)
    weight_n_bom_computed = fields.Float(_('NBOM Weight Computed'),
                                         readonly=True,
                                         digits='Stock Weight', default=0)

    @api.model_create_multi
    def create(self, vals):
        """
            Creating a product weight is set equal to weight_net and vice-versa
        """
        for val_dict in vals:
            weight = val_dict.get('weight', 0)
            weight_cad = val_dict.get('weight_cad', 0)
            if weight_cad and not weight:
                val_dict['weight'] = weight_cad
            elif weight and not weight_cad:
                val_dict['weight_cad'] = weight
        return super().create(vals)

    @api.onchange('automatic_compute_selection','weight_additional')
    def on_change_automatic_compute(self):
        """
            Compute weight due to selection choice
        """
        if self.automatic_compute_selection == 'use_cad':
            self.weight = self.weight_additional + self.weight_cad 
        elif self.automatic_compute_selection == 'use_normal_bom':
            self.weight = self.weight_additional + self.weight_n_bom_computed

    def compute_bom_weight(self):
        """
            - Compute first founded Normal Bom weight
            - Compute and set weight for all products and boms during computation
        """
        bom_obj = self.env['mrp.bom']
        for prod_brws in self:

            def recursion_bom(product_brws):
                product_tmpl_id = product_brws.product_tmpl_id.id
                if not product_tmpl_id:
                    logging.warning('No Product Template is set for product {} '.format(product_brws.id))
                bom_brws_list = bom_obj.search([('type', '=', 'normal'), ('product_tmpl_id', '=', product_tmpl_id)])
                is_user_admin = self.is_user_weight_admin()
                if not bom_brws_list:
                    self.common_weight_compute(product_brws, is_user_admin, product_brws.weight)
                else:
                    for bom_brws in bom_brws_list:
                        bom_total_weight = 0
                        for bom_line_brws in bom_brws.bom_line_ids:
                            recursion_bom(bom_line_brws.product_id)
                            product_weight = bom_line_brws.product_id.weight
                            line_amount = product_weight * bom_line_brws.product_qty
                            bom_total_weight = bom_total_weight + line_amount
                        product_brws.write({'weight_n_bom_computed': bom_total_weight})
                        product_brws.weight_n_bom_computed = bom_total_weight
                        if product_brws.engineering_state not in [RELEASED_STATUS, OBSOLATED_STATUS] or (
                                product_brws.engineering_state in [RELEASED_STATUS, OBSOLATED_STATUS] and is_user_admin):
                            bom_brws.write({'weight_net': bom_total_weight})
                        self.common_weight_compute(product_brws, is_user_admin, product_brws.weight_n_bom_computed)
                        break

            recursion_bom(prod_brws)

    def common_weight_compute(self, product_product_id, is_user_admin, to_add=0.0):
        """
            Common compute and set weight in single product
        """

        def common_set(product_product_id):
            common_weight = False
            if product_product_id.automatic_compute_selection == 'use_cad':
                common_weight = product_product_id.weight_cad + product_product_id.weight_additional
            elif product_product_id.automatic_compute_selection == 'use_normal_bom':
                common_weight = product_product_id.weight_additional + to_add
            if common_weight!=False:
                product_product_id.write({'weight': common_weight})

        if product_product_id.engineering_state in [RELEASED_STATUS, OBSOLATED_STATUS]:
            if is_user_admin:
                common_set(product_product_id)
        else:
            common_set(product_product_id)

    def is_user_weight_admin(self):
        """
            Verify if logged user is a weight admin
        """
        group_brws = self.env['res.groups'].search(
            [('name', '=', 'PLM / Weight Admin')])  # Same name must be used in data record file
        if group_brws:
            if self.env.user in group_brws.users:
                return True
        return False

    def compute_bom_weight_action(self):
        """
            Function called form xml action to compute and set weight for all selected products and boms
        """
        for prod_brws in self:
            prod_brws.compute_bom_weight()
