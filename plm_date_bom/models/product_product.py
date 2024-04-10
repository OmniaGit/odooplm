# -*- encoding: utf-8 -*-
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

from odoo import models
from odoo import api


class ProductExtension(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'
    
    @api.model
    def updateObsoleteRecursive(self,
                                product_product_id,
                                presentsFlag=True):
        mrp_bom_id = self.env['mrp.bom']
        struct = product_product_id.getParentBomStructure()
        
        def recursion(struct2, isRoot=False):
            for vals, parentsList in struct2:
                bom_id = vals.get('bom_id', False)
                if bom_id:
                    bomBrws = mrp_bom_id.browse(bom_id)
                    bomBrws._obsolete_compute()
                    if not isRoot:
                        bomBrws.obsolete_presents_recursive = presentsFlag
                recursion(parentsList)

        recursion(struct, isRoot=True)

    def update_used_bom(self, product_product_id):
        mrp_bom_line = self.env['mrp.bom.line']
        product_computed = []
        #
        def _update_used_bom(product_product_id):
            if product_product_id.id in product_computed:
                return
            product_computed.append(product_product_id.id)
            #
            for mrp_bom_line_id in mrp_bom_line.search([('product_id','=',product_product_id.id),
                                                        ('bom_id.type','not in',['ebom'])]):
                bom_id = mrp_bom_line_id.bom_id
                bom_id.sudo().obsolete_presents_recursive=True
                bom_id.sudo().obsolete_presents = True
                bom_id.sudo().obsolete_presents_computed = True
                for product_product_id in bom_id.product_tmpl_id.product_variant_ids:
                    _update_used_bom(product_product_id)
        #
        _update_used_bom(product_product_id)
        
    def write(self, vals):
        res = super(ProductExtension, self).write(vals)
        statePresent = vals.get('state', None)
        if statePresent == 'obsoleted':
            # Here I force compute obsolete presents flag in all boms
            for product_template_id in self:
                for product_product_id in product_template_id.product_variant_ids:
                    #self.updateObsoleteRecursive(product_product_id)
                    self.update_used_bom(product_product_id)
        return res

