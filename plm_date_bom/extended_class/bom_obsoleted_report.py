# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
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
Created on 19 Jul 2016

@author: Daniel Smerghetto
'''
from openerp.osv import osv
from openerp.report import report_sxw
from openerp import _
import time


def _translate(value):
    return _(value)


def get_bom_report(myObject, recursion=False, flat=False, leaf=False, level=1, summarize=False):

    def summarize_level(bomObj, recursion=False, flat=False, level=1, leaf=False, parentKey='', summarize=False):
        if leaf:
            recursion = True
        for l in bomObj.bom_line_ids:
            res = {}
            product = l.product_id.product_tmpl_id
            myKey = product.name
            if recursion or leaf or flat:
                myNewBom = None
                for bomBws in l.product_id.bom_ids:
                    if bomBws.type == l.bom_id.type:
                        myNewBom = bomBws
                        break
                if leaf and not myNewBom:
                    myKey = 'leaf_' + myKey
                elif not flat:
                    myKey = parentKey + myKey + '_' + str(level)
                if myNewBom:
                    if flat or myKey not in listed.keys():
                        summarize_level(myNewBom, recursion, flat, level + 1, leaf, myKey, summarize)
            if myKey in listed.keys() and summarize:
                listed[myKey]['pqty'] = listed[myKey].get('pqty', 0) + l.product_qty
            else:
                res['name'] = product.engineering_code
                res['item'] = l.itemnum
                res['pname'] = product.engineering_code
                res['pdesc'] = _(product.description)
                res['pcode'] = l.product_id.default_code
                res['previ'] = product.engineering_revision
                res['pqty'] = l.product_qty
                res['uname'] = l.product_uom.name
                res['pweight'] = product.weight
                res['code'] = l.product_id.default_code
                res['level'] = level
                res['prodBrws'] = l.product_id
                res['prodTmplBrws'] = product
                if leaf and 'leaf_' not in myKey:
                    continue
                if product.state == 'obsoleted':
                    listed[myKey] = res
                    LL = sortIndex.setdefault(res['item'], [])
                    LL.append(myKey)
                    sortIndex[res['item']] = LL

    listed = {}
    sortIndex = {}
    summarize_level(myObject, recursion, flat, level, leaf, '', summarize)
    kkk = sortIndex.keys()
    kkk.sort()
    out = []
    for i in kkk:
        for pName in sortIndex.get(i, []):
            out.append(listed.get(pName, {}))
    return out


class bom_structure_obsoleted(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_obsoleted, self).__init__(cr, uid, name, context=context)
        self.keyIndex = 0
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'trans': _translate,
            'context': context,
        })

    def get_children(self, myObject, level=1):
        return get_bom_report(myObject, recursion=True, flat=False, leaf=False, level=1, summarize=False)

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
        return _(result)


class report_plm_bom_obsoleted(osv.AbstractModel):
    _name = 'report.plm_date_bom.plm_bom_obsoleted'
    _inherit = 'report.abstract_report'
    _template = 'plm_date_bom.plm_bom_obsoleted'
    _wrapped_report_class = bom_structure_obsoleted
