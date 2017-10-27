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
'''
Created on 25/mag/2016

@author: mboscolo
'''

import logging
from odoo import models
from odoo import fields
from odoo import osv
from odoo import api
from odoo import _
_logger = logging.getLogger(__name__)


class plm_temporary_cutted(osv.osv.osv_memory):
    _inherit = 'plm.temporary'
    cutted_part_explosion = fields.Selection([('none', 'None'),
                                              ('explode', 'Explode'),
                                              ('replace', 'Replace')],
                                             _('Cutted Part Action'),
                                             default='none')

    @api.multi
    def action_create_normalBom(self):
        selectdIds = self.env.context.get('active_ids', [])
        objType = self.env.context.get('active_model', '')
        responce = super(plm_temporary_cutted, self).action_create_normalBom()
        for plmTmpObj in self:
            explosion_action = plmTmpObj.cutted_part_explosion
            if explosion_action != 'none':
                product_product_type_object = self.env.get(objType)
                mrp_bom_type_object = self.env.get('mrp.bom')
                mrp_bom_line_type_object = self.env.get('mrp.bom.line')
    
                def cuttedPartAction(bomLineBrws):
                    materiaPercentage = (1 + bomLineBrws.product_id.wastage_percent)
                    xMaterial = (bomLineBrws.product_id.row_material_xlenght * materiaPercentage) + bomLineBrws.product_id.material_added
                    yMaterial = (bomLineBrws.product_id.row_material_ylenght * materiaPercentage) + bomLineBrws.product_id.material_added
                    xRawMaterialLenght = bomLineBrws.product_id.row_material.row_material_xlenght
                    yRawMaterialLenght = bomLineBrws.product_id.row_material.row_material_ylenght
                    xQty = xMaterial / (1 if xRawMaterialLenght == 0 else xRawMaterialLenght)
                    yQty = yMaterial / (1 if yRawMaterialLenght == 0 else yRawMaterialLenght)
                    qty = xQty * yQty
                    commonValues = {'x_leght': xMaterial,
                                    'y_leght': yMaterial,
                                    'product_qty': 1 if qty == 0 else qty,  # set to 1 because odoo dose not manage qty==0
                                    'product_id': bomLineBrws.product_id.row_material.id,
                                    'product_rounding': bomLineBrws.product_id.bom_rounding}
                    if explosion_action == 'replace':
                        commonValues['product_qty'] = bomLineBrws.product_qty * commonValues['product_qty']
                        bomLineBrws.write(commonValues)
                    else:
                        idTemplate = bomLineBrws.product_id.product_tmpl_id.id
                        bomBrwsList = mrp_bom_type_object.search([('product_tmpl_id', '=', idTemplate),
                                                                  ('type', '=', 'normal')])
    
                        if not bomBrwsList:
                            values = {'product_tmpl_id': idTemplate,
                                      'type': 'normal'}
                            newBomBrws = mrp_bom_type_object.create(values)
                            values = {'type': 'normal',
                                      'bom_id': newBomBrws.id}
                            values.update(commonValues)
                            mrp_bom_line_type_object.create(values)
                        else:
                            for bomBrws in bomBrwsList:
                                if len(bomBrws.bom_line_ids) > 1:
                                    raise osv.osv.except_osv(_('Bom Generation Error'), 'Bom "%s" has more than one line, please check better.' % (bomBrws.product_tmpl_id.engineering_code))
                                for bomLineBrws in bomBrws.bom_line_ids:
                                    logging.info("Bom line updated %r" % bomLineBrws.id)
                                    bomLineBrws.write(commonValues)
                                    return
    
                def actionOnBom(productIds):
                    for productBrowse in product_product_type_object.browse(productIds):
                        idTemplate = productBrowse.product_tmpl_id.id
                        bomBrwsList = mrp_bom_type_object.search([('product_tmpl_id', '=', idTemplate),
                                                                  ('type', '=', 'normal')])
                        for bomObj in bomBrwsList:
                            for bomLineBrws in bomObj.bom_line_ids:
                                if bomLineBrws.product_id.row_material:
                                    cuttedPartAction(bomLineBrws)
                                else:
                                    actionOnBom([bomLineBrws.product_id.id])

                actionOnBom(selectdIds)
            return responce

plm_temporary_cutted()
