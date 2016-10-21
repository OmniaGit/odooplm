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
Created on Apr 14, 2016

@author: Daniel Smerghetto
'''

from odoo import api
from odoo import models
from odoo.osv import osv
from odoo.report import report_sxw
from operator import itemgetter
from odoo import _
import odoo
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
                res['item'] = l.itemnum
                res['pqty'] = l.product_qty
                res['level'] = level
                res['lineBrws'] = l
                res['prodTmplBrws'] = product
                if leaf and 'leaf_' not in myKey:
                    continue
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


def BomSort(myObject):
    valid = False
    bomobject = []
    res = {}
    index = 0
    for l in myObject:
        res[str(index)] = l.itemnum
        index += 1
        if l.itemnum > 0:
            valid = True
    if not valid:
        res = {}
        index = 0
        for l in myObject:
            res[str(index)] = l.product_id.product_tmpl_id.name
            index += 1
    items = res.items()
    items.sort(key=itemgetter(1))
    for res in items:
        bomobject.append(myObject[int(res[0])])
    return bomobject


class bom_structure_all_custom_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(bom_structure_all_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'trans': _translate,
            'context': context,
        })

    def get_children(self, myObject, level=0):
        return get_bom_report(myObject, recursion=True, flat=False, leaf=False, level=1, summarize=False)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)


class bom_structure_one_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_one_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'trans': _translate,
            'context': context,
        })

    def get_children(self, myObject, level=0):
        return get_bom_report(myObject, recursion=False, flat=False, leaf=False, level=1, summarize=False)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)


class bom_structure_all_sum_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_all_sum_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'trans': _translate,
            'context': context,
        })

    def get_children(self, myObject, level=1):
        return get_bom_report(myObject, recursion=True, flat=False, leaf=False, level=level, summarize=True)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)


class bom_structure_one_sum_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_one_sum_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'trans': _translate,
            'context': context,
        })

    def get_children(self, myObject):
        return get_bom_report(myObject, summarize=True)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)


class bom_structure_leaves_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_leaves_custom_report, self).__init__(cr, uid, name, context=context)
        self.keyIndex = 0
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'trans': _translate,
            'context': context,
        })

    def get_children(self, myObject, level=1):
        return get_bom_report(myObject, leaf=True, level=level, summarize=True)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)


class bom_structure_flat_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_flat_custom_report, self).__init__(cr, uid, name, context=context)
        self.keyIndex = 0
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
            'trans': _translate,
            'context': context,
        })

    def get_children(self, myObject, level=1):
        return get_bom_report(myObject, recursion=True, flat=True, leaf=False, level=level, summarize=True)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)


class report_plm_bom_all(osv.AbstractModel):
    _name = 'report.plm.bom_structure_all'
    _inherit = 'report.abstract_report'
    _template = 'plm.bom_structure_all'
    _wrapped_report_class = bom_structure_all_custom_report


class report_plm_bom_one(osv.AbstractModel):
    _name = 'report.plm.bom_structure_one'                          # May it is equal to "_template" keyword
    _inherit = 'report.abstract_report'                             # Every time inherit from abstract report
    _template = 'plm.bom_structure_one'                             # Searched as "report_name" in ir.actions.act.window
    _wrapped_report_class = bom_structure_one_custom_report


class report_plm_bom_all_sum(osv.AbstractModel):
    _name = 'report.plm.bom_structure_all_sum'
    _inherit = 'report.abstract_report'
    _template = 'plm.bom_structure_all_sum'
    _wrapped_report_class = bom_structure_all_sum_custom_report


class report_plm_bom_one_sum(osv.AbstractModel):
    _name = 'report.plm.bom_structure_one_sum'
    _inherit = 'report.abstract_report'
    _template = 'plm.bom_structure_one_sum'
    _wrapped_report_class = bom_structure_one_sum_custom_report


class report_plm_bom_leaves_sum(osv.AbstractModel):
    _name = 'report.plm.bom_structure_leaves'
    _inherit = 'report.abstract_report'
    _template = 'plm.bom_structure_leaves'
    _wrapped_report_class = bom_structure_leaves_custom_report


class report_plm_bom_flat(osv.AbstractModel):
    _name = 'report.plm.bom_structure_flat'
    _inherit = 'report.abstract_report'
    _template = 'plm.bom_structure_flat'
    _wrapped_report_class = bom_structure_flat_custom_report
