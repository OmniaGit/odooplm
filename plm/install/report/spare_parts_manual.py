## -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

'''
Created on Apr 15, 2016

@author: Daniel Smerghetto
'''

from openerp import api
from openerp import models
from openerp.osv import osv
from openerp.report import report_sxw
from operator import itemgetter
from openerp import _
import time

HEADERS =       ['BOM Name', 'Pos.', 'Product Name', 'Rev',  'Description', 'Producer', 'producer P/N', 'Qty', 'UoM',    'Weight']
FIELDS_ORDER =  ['',        'item',  'pname',        'previ','pdesc',       'producer', 'producer_pn',  'pqty','uname',  'pweight']


def _translate(value):
    return _(value)


def BomSort(myObject):
    bomobject = []
    res = {}
    index = 0
    for l in myObject:
        res[str(index)] = l.itemnum
        index += 1
    items = res.items()
    items.sort(key=itemgetter(1))
    for res in items:
        bomobject.append(myObject[int(res[0])])
    return bomobject


def get_parent(myObject):
    return [
               myObject.product_tmpl_id.name,
               '',
               _(myObject.product_tmpl_id.name) or _(myObject.product_tmpl_id.default_code),
               myObject.product_tmpl_id.engineering_revision,
               _(myObject.product_tmpl_id.description),
               '',
               '',
               myObject.product_qty,
               '',
               myObject.weight_net,
              ]


class bom_spare_one_sum_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_spare_one_sum_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'headers': HEADERS,
            'get_parent': get_parent,
            'keys_order': FIELDS_ORDER,
        })

    def get_children(self, myObject, level=0):
        result = []

        def _get_rec(bomobject, level):
            myObject = BomSort(bomobject)
            tmp_result = []
            listed = {}
            keyIndex = 0
            for l in myObject:
                res = {}
                product = l.product_id.product_tmpl_id
                if product.name in listed.keys():
                    res = tmp_result[listed[product.name]]
                    res['pqty'] = res['pqty'] + l.product_qty
                    tmp_result[listed[product.name]] = res
                else:
                    producer = ''
                    producer_pn = ''
                    for sellerObj in product.seller_ids:
                        producer = sellerObj.name.name
                        producer_pn = sellerObj.product_name or sellerObj.product_code
                    res['name'] = product.name
                    res['item'] = l.itemnum
                    res['pname'] = l.product_id.name
                    res['pdesc'] = product.description
                    res['pcode'] = l.product_id.default_code
                    res['previ'] = product.engineering_revision
                    res['pqty'] = l.product_qty
                    res['uname'] = l.product_uom.name
                    res['pweight'] = product.weight
                    res['code'] = l.product_id.default_code
                    res['level'] = level
                    res['producer'] = producer
                    res['producer_pn'] = producer_pn
                    tmp_result.append(res)
                    listed[product.name] = keyIndex
                    keyIndex += 1
            return result.extend(tmp_result)

        _get_rec(myObject, level + 1)

        return result

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
        return _(result)


class report_plm_bom_flat(osv.AbstractModel):
    _name = 'report.plm.bom_spare_one_sum'
    _inherit = 'report.abstract_report'
    _template = 'plm.bom_spare_one_sum'
    _wrapped_report_class = bom_spare_one_sum_custom_report
