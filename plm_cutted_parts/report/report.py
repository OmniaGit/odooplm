##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 28/mag/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
Created on 28/mag/2016

@author: mboscolo
"""
from odoo import _
from odoo import api
from odoo import models


class ReportDocumentPdf(models.AbstractModel):
    _name = 'report.plm_cutted_parts.bom_structure_all_cutted'
    _description = "Report PLM cutted parts bom structure all cutted"

    def get_children(self, my_object, level=0):
        result = {}

        def _get_rec(bom_object, level, parent_qty=1):
            for l in bom_object.bom_line_ids:
                if l.product_id.is_row_material:
                    eng_code = l.product_id.engineering_code
                    res = {}
                    product = l.product_id.product_tmpl_id
                    res['name'] = product.name
                    res['item'] = l.itemnum
                    res['ancestor'] = l.bom_id.product_id
                    res['p_name'] = product.name
                    res['p_desc'] = _(product.name)
                    res['p_code'] = l.product_id.default_code
                    res['p_rev'] = product.engineering_revision
                    res['p_qty'] = l.product_qty * 1 if parent_qty < 1 else parent_qty
                    res['u_name'] = l.product_uom.name
                    res['p_weight'] = product.weight
                    res['code'] = eng_code
                    res['level'] = level
                    res['prod_brws'] = l.product_id
                    res['prod_tmpl_brws'] = product
                    res['x_length'] = l.x_leght
                    res['y_length'] = l.y_leght
                    spool_list = result.get(eng_code, [])
                    spool_list.append(res)
                    result[eng_code] = spool_list
                    continue

                for bom_id in l.product_id.bom_ids:
                    if bom_id.type == l.bom_id.type:
                        _get_rec(bom_id, level + 1, l.product_qty)
            return list(result.values())
        children = _get_rec(my_object, level + 1)
        return children

    def bom_type(self, my_object):
        result = dict(self.env.get(my_object._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(my_object.type, '')
        return _(result)

    @api.model
    def _get_report_values(self, docids, data=None):
        documents = self.env['mrp.bom'].browse(docids)
        return {'docs': documents,
                'get_children': self.get_children,
                'bom_type': self.bom_type,
                'context': self.env.context}
