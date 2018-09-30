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
from odoo import osv
from odoo import api
from odoo import _

_logger = logging.getLogger(__name__)


class PlmTemporaryCutted(osv.osv.osv_memory):
    _inherit = 'plm.temporary'
    cutted_part_explosion = fields.Selection(
        [('none', 'None'),
         ('explode', 'Explode'),
         ('replace', 'Replace')],
        _('Cutted Part Action'),
        default='none')

    @api.multi
    def action_create_normalBom(self):
        selected_ids = self.env.context.get('active_ids', [])
        obj_type = self.env.context.get('active_model', '')
        response = super(PlmTemporaryCutted, self).action_create_normalBom()
        for plmTmpObj in self:
            explosion_action = plmTmpObj.cutted_part_explosion
            if explosion_action != 'none':
                product_product_type_object = self.env.get(obj_type)
                mrp_bom_type_object = self.env.get('mrp.bom')
                mrp_bom_line_type_object = self.env.get('mrp.bom.line')

                def cutted_part_action(bom_line_brws):
                    material_percentage = (1 + bom_line_brws.product_id.wastage_percent)
                    x_material = (bom_line_brws.product_id.row_material_x_length * material_percentage) + bom_line_brws.product_id.material_added
                    y_material = (bom_line_brws.product_id.row_material_y_length * material_percentage) + bom_line_brws.product_id.material_added
                    x_raw_material_length = bom_line_brws.product_id.row_material.row_material_xlength
                    y_raw_material_length = bom_line_brws.product_id.row_material.row_material_ylength
                    x_qty = x_material / (1 if x_raw_material_length == 0 else x_raw_material_length)
                    y_qty = y_material / (1 if y_raw_material_length == 0 else y_raw_material_length)
                    qty = x_qty * y_qty
                    common_values = {'x_length': x_material,
                                    'y_length': y_material,
                                    'product_qty': 1 if qty == 0 else qty,
                                    # set to 1 because odoo dose not manage qty==0
                                    'product_id': bom_line_brws.product_id.row_material.id,
                                    'product_rounding': bom_line_brws.product_id.bom_rounding}
                    if explosion_action == 'replace':
                        common_values['product_qty'] = bom_line_brws.product_qty * common_values['product_qty']
                        bom_line_brws.write(common_values)
                    else:
                        id_template = bom_line_brws.product_id.product_tmpl_id.id
                        bom_brws_list = mrp_bom_type_object.search([('product_tmpl_id', '=', id_template),
                                                                  ('type', '=', 'normal')])

                        if not bom_brws_list:
                            values = {'product_tmpl_id': id_template,
                                      'type': 'normal'}
                            new_bom_brws = mrp_bom_type_object.create(values)
                            values = {'type': 'normal',
                                      'bom_id': new_bom_brws.id}
                            values.update(common_values)
                            mrp_bom_line_type_object.create(values)
                        else:
                            for bom_brws in bom_brws_list:
                                if len(bom_brws.bom_line_ids) > 1:
                                    raise osv.osv.except_osv(_('Bom Generation Error'),
                                                             'Bom "%s" has more than one line, please check better.' % (
                                                                 bom_brws.product_tmpl_id.engineering_code))
                                for bom_line_brws in bom_brws.bom_line_ids:
                                    logging.info("Bom line updated %r" % bom_line_brws.id)
                                    bom_line_brws.write(common_values)
                                    return

                def action_on_bom(product_ids):
                    for productBrowse in product_product_type_object.browse(product_ids):
                        id_template = productBrowse.product_tmpl_id.id
                        bom_brws_list = mrp_bom_type_object.search([('product_tmpl_id', '=', id_template),
                                                                  ('type', '=', 'normal')])
                        for bomObj in bom_brws_list:
                            for bom_line_brws in bomObj.bom_line_ids:
                                if bom_line_brws.product_id.row_material:
                                    cutted_part_action(bom_line_brws)
                                else:
                                    action_on_bom([bom_line_brws.product_id.id])

                action_on_bom(selected_ids)
            return response
