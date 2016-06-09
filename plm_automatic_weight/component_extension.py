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

from openerp        import models
from openerp        import fields
from openerp        import api
from openerp        import SUPERUSER_ID
from openerp        import _
from openerp        import osv
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class PlmComponent(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    automatic_compute = fields.Boolean(_('Automatic BOM compute'), default=False)
    weight_additional = fields.Float(_('Additional Weight'), digits_compute=dp.get_precision('Stock Weight'), default=0)
    weight_cad = fields.Float(_('CAD Weight'), readonly=True, digits_compute=dp.get_precision('Stock Weight'), default=0)
    weight_ebom_computed = fields.Float(_('EBOM Weight Computed'), readonly=True, digits_compute=dp.get_precision('Stock Weight'), default=0)

    @api.onchange('automatic_compute')
    def on_change_automatic_compute(self):
        if self.automatic_compute:
            prodBrws = self.search([('engineering_code', '=', self.engineering_code), ('engineering_revision', '=', self.engineering_revision)])
            prodBrws.automatic_compute = True
            self.computeBomWeight(prodBrws)
        else:
            self.weight = self.weight_cad

    @api.onchange('weight_additional')
    def on_change_weight_additional(self):
        if self.automatic_compute:
            self.weight = self.weight_ebom_computed + self.weight_additional

    @api.multi
    def computeBomWeight(self, prodBrws):
        bomObj = self.env['mrp.bom']

        def recursionBom(productBrws):
            productTmplId = productBrws.product_tmpl_id.id
            if not productTmplId:
                logging.warning('No Product Template is set for product %s '  % (productBrws.id))
            bomBrwsList = bomObj.search([('type', '=', 'ebom'), ('product_tmpl_id', '=', productTmplId)])
            isUserAdmin = self.isUserWeightAdmin()
            if not bomBrwsList:
                self.commonWeightCompute(productBrws, isUserAdmin, productBrws.weight_cad)
            else:
                for bomBrws in bomBrwsList:
                    bomTotalWeight = 0
                    for bomLineBrws in bomBrws.bom_line_ids:
                        recursionBom(bomLineBrws.product_id)
                        productWeight = bomLineBrws.product_id.weight
                        bomTotalWeight = bomTotalWeight + productWeight
                    productBrws.write({'weight_ebom_computed': bomTotalWeight})
                    productBrws.weight_ebom_computed = bomTotalWeight
                    if productBrws.state not in ['released', 'obsoleted'] or (productBrws.state in ['released', 'obsoleted'] and isUserAdmin):
                        bomBrws.write({'weight_net': bomTotalWeight})
                    self.commonWeightCompute(productBrws, isUserAdmin, productBrws.weight_ebom_computed)
                    break

        recursionBom(prodBrws)

    def commonWeightCompute(self, productBrws, isUserAdmin, toAdd):
        def commonSet(productB):
                if productB.automatic_compute:
                    common = toAdd + productB.weight_additional
                    productB.write({'weight': common})
                    productB.weight = common
                else:
                    productB.write({'weight': productB.weight_cad})
                    productB.weight = productB.weight_cad

        if productBrws.state in ['released', 'obsoleted']:
            if isUserAdmin:
                commonSet(productBrws)
        else:
                commonSet(productBrws)

    def isUserWeightAdmin(self):
        groupBrws = self.env['res.groups'].search([('name', '=', 'PLM / Weight Admin')])
        if groupBrws:
            if self.env.user in groupBrws.users:
                return True
        return False

PlmComponent()


class MrpBomExtension(models.Model):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

    @api.multi
    def computeBomWeightAction(self):
        pass

MrpBomExtension()
