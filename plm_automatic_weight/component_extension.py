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
Created on May 25, 2016

@author: Daniel Smerghetto
'''

from openerp import models
from openerp import fields
from openerp import api
from openerp import _
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class PlmComponent(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    automatic_compute_selection = fields.Selection([('use_net', _('Use Net Weight')),
                                                    ('use_cad', _('Use CAD Weight')),
                                                    ('use_normal_bom', _('Use Normal Bom'))],
                                                   _('Weight compute mode'),
                                                   default='use_net',
                                                   help=_("""Set "Use Net Weight" to use only gross weight. Set "Use CAD Weight" to use CAD weight + Additional Weight as gross weight. Set "Use Normal Bom" to use NBOM Weight Computed + Additional weight as gross weight.""")
                                                   )
    weight_additional = fields.Float(_('Additional Weight'), digits_compute=dp.get_precision('Stock Weight'), default=0)
    weight_cad = fields.Float(_('CAD Weight'), readonly=True, digits_compute=dp.get_precision('Stock Weight'), default=0)
    weight_nbom_computed = fields.Float(_('NBOM Weight Computed'), readonly=True, digits_compute=dp.get_precision('Stock Weight'), default=0)

    @api.model
    def create(self, vals):
        '''
            Creating a product weight is set equal to weight_net and vice-versa
        '''
        weight = vals.get('weight', 0)
        weight_cad = vals.get('weight_cad', 0)
        if weight_cad and not weight:
            vals['weight'] = weight_cad
        elif weight and not weight_cad:
            vals['weight_cad'] = weight
        return super(PlmComponent, self).create(vals)

    @api.onchange('automatic_compute_selection')
    def on_change_automatic_compute(self):
        '''
            Compute weight due to selection choice
        '''
        if self.automatic_compute_selection == 'use_cad':
            self.weight = self.weight_cad + self.weight_additional
        elif self.automatic_compute_selection == 'use_normal_bom':
            self.weight = self.weight_additional + self.weight_nbom_computed

    @api.onchange('weight_additional')
    def on_change_weight_additional(self):
        '''
            Compute weight due to additional weight change
        '''
        if self.automatic_compute_selection == 'use_normal_bom':
            self.weight = self.weight_nbom_computed + self.weight_additional
        elif self.automatic_compute_selection == 'use_cad':
            self.weight = self.weight_cad + self.weight_additional

    @api.multi
    def computeBomWeight(self):
        '''
            - Compute first founded Normal Bom weight
            - Compute and set weight for all products and boms during computation
        '''
        for prodBrws in self:
            bomObj = self.env['mrp.bom']

            def recursionBom(productBrws):
                productTmplId = productBrws.product_tmpl_id.id
                if not productTmplId:
                    logging.warning('No Product Template is set for product %s ' % (productBrws.id))
                bomBrwsList = bomObj.search([('type', '=', 'normal'), ('product_tmpl_id', '=', productTmplId)])
                isUserAdmin = self.isUserWeightAdmin()
                if not bomBrwsList:
                    self.commonWeightCompute(productBrws, isUserAdmin, productBrws.weight_cad)
                else:
                    for bomBrws in bomBrwsList:
                        bomTotalWeight = 0
                        for bomLineBrws in bomBrws.bom_line_ids:
                            recursionBom(bomLineBrws.product_id)
                            productWeight = bomLineBrws.product_id.weight
                            lineAmount = productWeight * bomLineBrws.product_qty
                            bomTotalWeight = bomTotalWeight + lineAmount
                        productBrws.write({'weight_nbom_computed': bomTotalWeight})
                        productBrws.weight_nbom_computed = bomTotalWeight
                        if productBrws.state not in ['released', 'obsoleted'] or (productBrws.state in ['released', 'obsoleted'] and isUserAdmin):
                            bomBrws.write({'weight_net': bomTotalWeight})
                        self.commonWeightCompute(productBrws, isUserAdmin, productBrws.weight_nbom_computed)
                        break

            recursionBom(prodBrws)

    def commonWeightCompute(self, productBrws, isUserAdmin, toAdd):
        '''
            Common compute and set weight in single product
        '''
        def commonSet(productB):
            if productB.automatic_compute_selection == 'use_cad':
                commonWeight = productB.weight_cad + productB.weight_additional
                productB.write({'weight': commonWeight})
                productB.weight = commonWeight
            elif productB.automatic_compute_selection == 'use_normal_bom':
                common = toAdd + productB.weight_additional
                productB.write({'weight': common})
                productB.weight = common

        if productBrws.state in ['released', 'obsoleted']:
            if isUserAdmin:
                commonSet(productBrws)
        else:
            commonSet(productBrws)

    def isUserWeightAdmin(self):
        '''
            Verify if logged user is a weight admin
        '''
        groupBrws = self.env['res.groups'].search([('name', '=', 'PLM / Weight Admin')])    # Same name must be used in data record file
        if groupBrws:
            if self.env.user in groupBrws.users:
                return True
        return False

    @api.multi
    def computeBomWeightAction(self):
        '''
            Function called form xml action to compute and set weight for all selected products and boms
        '''
        for prodBrws in self:
            prodBrws.computeBomWeight()

PlmComponent()
