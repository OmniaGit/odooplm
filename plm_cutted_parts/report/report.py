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
'''
Created on 28/mag/2016

@author: mboscolo
'''
from openerp import _
from openerp.osv import osv
from openerp.report import report_sxw


class bom_structure_cutted_parts(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(bom_structure_cutted_parts, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'context': context,
        })

    def get_children(self, myObject, level=0):
        result = {}

        def _get_rec(bomobject, level, parentQty=1):
            for l in bomobject.bom_line_ids:
                if l.product_id.is_row_material:
                    eng_code = l.product_id.engineering_code
                    res = {}
                    product = l.product_id.product_tmpl_id
                    res['name'] = product.name
                    res['item'] = l.itemnum
                    res['ancestor'] = l.bom_id.product_id
                    res['pname'] = product.name
                    res['pdesc'] = _(product.description)
                    res['pcode'] = l.product_id.default_code
                    res['previ'] = product.engineering_revision
                    res['pqty'] = l.product_qty * 1 if parentQty < 1 else parentQty
                    res['uname'] = l.product_uom_id.name
                    res['pweight'] = product.weight
                    res['code'] = eng_code
                    res['level'] = level
                    res['prodBrws'] = l.product_id
                    res['prodTmplBrws'] = product
                    res['x_leght'] = l.x_leght
                    res['y_leght'] = l.y_leght
                    spoolList = result.get(eng_code, [])
                    spoolList.append(res)
                    result[eng_code] = spoolList
                    continue

                for bomId in l.product_id.bom_ids:
                    if bomId.type == l.bom_id.type:
                        _get_rec(bomId, level + 1, l.product_qty)
            return result.values()
        children = _get_rec(myObject, level + 1)
        return children

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
        return _(result)


class bom_structure_all_cutted(osv.AbstractModel):
    _name = 'report.plm_cutted_parts.bom_structure_all_cutted'
    _inherit = 'report.abstract_report'
    _template = 'plm_cutted_parts.bom_structure_all_cutted'
    _wrapped_report_class = bom_structure_cutted_parts
