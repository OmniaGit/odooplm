##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 25/mag/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
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
Created on 25/mag/2016

@author: mboscolo
"""

import logging
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PlmTemporaryCutted(models.TransientModel):
    _inherit = 'plm.temporary'
    
    cutted_part_explosion = fields.Selection(
        [('none', 'None'),
         ('explode', 'Explode'),
         ('replace', 'Replace')],
        _('Cutted Part Action'),
        default='none')

    @api.model
    def action_on_bom(self,
                      product_ids,
                      explosion_action):
        product_product_type_object = self.env.get('product.product')
        for productBrowseFinished in product_product_type_object.browse(product_ids):
            self._action_on_bom(productBrowseFinished, explosion_action)

    def _action_on_bom(self,
                       product_id,
                       explosion_action):
        """
        Compute the cutted parts explosion
        :product_id product.product odoo object
        :explosion_action ['none', 'explode', 'replace']
        """
        mrp_bom_o = self.env.get('mrp.bom')
        id_template = product_id.product_tmpl_id.id
        mrp_bom_ids = mrp_bom_o.search([('product_tmpl_id', '=', id_template),
                                        ('type', '=', 'normal')])
        if product_id.row_material:
            if mrp_bom_ids:
                for bom_line_id in mrp_bom_ids:
                    if bom_line_id.product_id.row_material.id!=product_id.row_material.id:
                        bom_line_id.row_material=product_id.row_material.id
                    self.cutted_part_action(bom_line_id, explosion_action)
                    break
            else: # no bom available
                vals = {
                    'product_id': product_id.id,
                    'product_tmpl_id': id_template,
                    'type': 'normal',
                    }
                mrp_bom_ids = mrp_bom_o.create(vals)
                for nbom in mrp_bom_ids:
                    line_vals = {
                        'bom_id': nbom.id,
                        'product_id': product_id.row_material.id,
                        'product_qty': 1,
                        'x_length': product_id.row_material_x_length,
                        'y_length': product_id.row_material_y_length,
                        'cutted_type': 'server',
                        'cutted_qty': product_id.row_material_factor,
                        }
                    bom_line_brws = self.env['mrp.bom.line'].create(line_vals)
                    bom_line_brws.computeCuttedTotalQty()
        else:
            for mrp_bom_id in mrp_bom_ids:
                for bom_line_brws in mrp_bom_id.bom_line_ids:
                    self._action_on_bom(bom_line_brws.product_id, explosion_action) # is raw material
                break
            
        if not mrp_bom_ids:
            product_product_raw_material_id = product_id.row_material
            if product_product_raw_material_id:
                mrp_bom_ids = mrp_bom_o.search([('product_tmpl_id', '=', id_template),
                                                ('type', '=', 'normal')])


    @api.model
    def cutted_part_action(self,
                           bom_line_brws,
                           explosion_action):
        """
        
        """
        mrp_bom_type_object = self.env.get('mrp.bom')
        mrp_bom_line_type_object = self.env.get('mrp.bom.line')
        if explosion_action == 'replace':
            x_len = mrp_bom_line_type_object.computeXLenghtByProduct(bom_line_brws.product_id)
            y_len = mrp_bom_line_type_object.computeYLenghtByProduct(bom_line_brws.product_id)
            to_write = {
                'product_id': bom_line_brws.product_id.row_material.id,
                'cutted_type': 'none',
                'product_qty': bom_line_brws.computeTotalQty(x_len, y_len, bom_line_brws.product_qty),
                'cutted_qty': bom_line_brws.product_id.row_material_factor,
                }
            bom_line_brws.write(to_write)
        elif explosion_action == 'explode':
            id_template = bom_line_brws.product_id.product_tmpl_id.id
            bom_brws_list = mrp_bom_type_object.search([('product_tmpl_id', '=', id_template),
                                                      ('type', '=', 'normal')
                                                      ])

            if not bom_brws_list:
                values = {'product_tmpl_id': id_template,
                          'product_id': bom_line_brws.product_id.id,
                          'type': 'normal'}
                new_bom_brws = mrp_bom_type_object.create(values)
                values = {'type': 'normal',
                          'bom_id': new_bom_brws.id,
                          'product_id': bom_line_brws.product_id.row_material.id,
                          'cutted_type': 'server',
                          'cutted_qty': bom_line_brws.product_id.row_material_factor,
                          }
                bom_line_brws = mrp_bom_line_type_object.create(values)
                bom_line_brws.computeCuttedTotalQty()
            else:
                for bom_brws in bom_brws_list:
                    cuttedLines = bom_brws.bom_line_ids.filtered(lambda line: line.cutted_type == 'server')
                    if len(cuttedLines) > 1:
                        raise UserError('Bom "%s" has more than one line, please check better.' % (bom_brws.product_tmpl_id.engineering_code))
                    for bom_line_brws in cuttedLines:
                        raw_mat = bom_line_brws.bom_id.product_id.row_material
                        if not bom_line_brws.bom_id.product_id.row_material:
                            raw_mat = bom_line_brws.bom_id.product_tmpl_id.product_variant_id.row_material
                        bom_line_brws.product_id = raw_mat.id
                        bom_line_brws.computeCuttedTotalQty()
                        logging.info("Bom line updated %r" % bom_line_brws.id)
                        return
        else:
            raise NotImplementedError('Cutted part action %r' % (explosion_action))

    def action_create_normalBom(self):
        """
        xml action called
        """
        selected_ids = self.env.context.get('active_ids', [])
        ctx = self.env.context.copy()
        for plmTmpObj in self:
            explosion_action = plmTmpObj.cutted_part_explosion
            ctx['cutted_part_explosion'] = explosion_action
            response = super(PlmTemporaryCutted, self.with_context(ctx)).action_create_normalBom()
            if explosion_action != 'none':
                self.action_on_bom(selected_ids, explosion_action)
            return response
