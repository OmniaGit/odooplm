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

from openerp import api
from openerp import models
from openerp.osv import osv
from openerp.report import report_sxw
from operator import itemgetter
from openerp import _
import time


def _translate(value):
    return _(value)


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


def SummarizeBom(bomobject, level=1, result={}, ancestorName=""):

    for l in bomobject:
        evaluate = True
        fatherName = l.bom_id.product_id.name
        productName = l.product_id.name
        fatherRef = "%s-%d" % (fatherName, level - 1)
        productRef = "%s-%s-%d" % (ancestorName, productName, level)
        if fatherRef in result:
            listed = result[fatherRef]
        else:
            result[fatherRef] = {}
            listed = {}

        if productRef in listed and listed[productRef]['father'] == fatherName:
            res = listed[productRef]
            res['pqty'] = res['pqty'] + l.product_qty
            evaluate = False
        else:
            res = {}
            res['product'] = l.product_id
            res['name'] = l.product_id.name
            res['ancestor'] = ancestorName
            res['father'] = fatherName
            res['pqty'] = l.product_qty
            res['level'] = level
            listed[productRef] = res

        result[fatherRef] = listed
        if evaluate:
            for bomId in l.product_id.bom_ids:
                if bomId.type == l.bom_id.type:
                    if bomId.bom_line_ids:
                        result.update(SummarizeBom(bomId.bom_line_ids, level + 1, result, fatherName))
                        break

    return result


def QuantityInBom(listedBoM={}, productName=""):
    found = []
    result = 0.0
    for fatherRef in listedBoM.keys():
        for listedName in listedBoM[fatherRef]:
            listedline = listedBoM[fatherRef][listedName]
            if (listedline['name'] == productName) and not (listedline['father'] in found):
                result += listedline['pqty'] * QuantityInBom(listedBoM, listedline['father'])
                found.append(listedline['father'])
                break
    if not found:
        result = 1.0
    return result


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
        result = []

        def _get_rec(bomobject, level):
            myObject = BomSort(bomobject)

            for l in myObject:
                res = {}
                product = l.product_id.product_tmpl_id
                res['name'] = product.name
                res['item'] = l.itemnum
                res['ancestor'] = l.bom_id.product_id
                res['pname'] = product.name
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
                result.append(res)
                for bomId in l.product_id.bom_ids:
                    if bomId.type == l.bom_id.type:
                        _get_rec(bomId.bom_line_ids, level + 1)
            return result

        children = _get_rec(myObject, level + 1)

        return children

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
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
        result = []

        def _get_rec(bomobject, level):
            myObject = BomSort(bomobject)
            for l in myObject:
                res = {}
                product = l.product_id.product_tmpl_id
                res['name'] = product.name
                res['item'] = l.itemnum
                res['pname'] = product.name
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
                result.append(res)
            return result

        children = _get_rec(myObject, level + 1)

        return children

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
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

    def get_children(self, myObject, level=0):
        result = []
        results = {}

        def _get_rec(bomobject, listedBoM, level, ancestor=""):
            listed = []
            myObject = BomSort(bomobject)
            tmp_result = []
            for l in myObject:
                productName = l.product_id.name
                if productName in listed:
                    continue
                res = {}
                listed.append(productName)
                fatherName = l.bom_id.product_id.name
                fatherRef = "%s-%d" % (fatherName, level - 1)
                if fatherRef in listedBoM.keys():
                    listedName = "%s-%s-%d" % (ancestor, productName, level)
                    if listedName in listedBoM[fatherRef]:
                        listedline = listedBoM[fatherRef][listedName]
                        product = listedline['product']
                        res['name'] = product.name
                        res['item'] = l.itemnum
                        res['pfather'] = fatherName
                        res['pname'] = product.name
                        res['pdesc'] = _(product.description)
                        res['pcode'] = l.product_id.default_code
                        res['previ'] = product.engineering_revision
                        res['pqty'] = listedline['pqty']
                        res['uname'] = l.product_uom.name
                        res['pweight'] = product.weight
                        res['code'] = l.product_id.default_code
                        res['level'] = level
                        res['prodBrws'] = l.product_id
                        res['prodTmplBrws'] = product
                        tmp_result.append(res)

                        for bomId in l.product_id.bom_ids:
                            if bomId.type == l.bom_id.type:
                                if bomId.bom_line_ids:
                                    buffer_obj = _get_rec(bomId.bom_line_ids, listedBoM, level + 1, fatherName)
                                    tmp_result.extend(buffer_obj)
            return tmp_result

        results = SummarizeBom(myObject, level + 1, results)
        result.extend(_get_rec(myObject, results, level + 1))

        return result

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
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
                    res['name'] = product.name
                    res['item'] = l.itemnum
                    res['pname'] = product.name
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
                    tmp_result.append(res)
                    listed[l.product_id.name] = keyIndex
                    keyIndex += 1
            return result.extend(tmp_result)

        _get_rec(myObject, level + 1)

        return result

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
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

    def get_children(self, myObject, level=0):
        result = []
        results = {}
        listed = []

        def _get_rec(bomobject, listedBoM, listed, level, ancestor=""):

            myObject = BomSort(bomobject)
            tmp_result = []
            for l in myObject:
                productName = l.product_id.name
                if productName in listed:
                    continue
                res = {}
                listed.append(productName)
                fatherName = l.bom_id.product_id.name
                fatherRef = "%s-%d" % (fatherName, level - 1)
                if fatherRef in listedBoM.keys():
                    listedName = "%s-%s-%d" % (ancestor, productName, level)
                    if listedName in listedBoM[fatherRef]:
                        listedline = listedBoM[fatherRef][listedName]
                        product = listedline['product']
                        productRef = "%s-%d" % (product.name, level)
                        if not productRef in listedBoM.keys():
                            quantity = QuantityInBom(listedBoM, product.name)
                            res['name'] = product.name
                            res['item'] = l.itemnum
                            res['pfather'] = fatherName
                            res['pname'] = product.name
                            res['pdesc'] = _(product.description)
                            res['pcode'] = l.product_id.default_code
                            res['previ'] = product.engineering_revision
                            res['pqty'] = quantity
                            res['uname'] = l.product_uom.name
                            res['pweight'] = product.weight
                            res['code'] = l.product_id.default_code
                            res['level'] = level
                            res['prodBrws'] = l.product_id
                            res['prodTmplBrws'] = product
                            tmp_result.append(res)

                        for bomId in l.product_id.bom_ids:
                            if bomId.type == l.bom_id.type:
                                if bomId.bom_line_ids:
                                    buffer_obj = _get_rec(bomId.bom_line_ids, listedBoM, listed, level + 1, fatherName)
                                    tmp_result.extend(buffer_obj)
            return tmp_result

        results = SummarizeBom(myObject, level + 1, results)
        result.extend(_get_rec(myObject, results, listed, level + 1))

        return result

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
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

    def get_children(self, myObject, level=0):
        result = []
        results = {}
        listed = []

        def _get_rec(bomobject, listedBoM, listed, level, ancestor=""):
            myObject = BomSort(bomobject)
            tmp_result = []
            for l in myObject:
                productName = l.product_id.name
                if productName in listed:
                    continue
                res = {}
                listed.append(productName)
                fatherName = l.bom_id.product_id.name
                fatherRef = "%s-%d" % (fatherName, level - 1)
                if fatherRef in listedBoM.keys():
                    listedName = "%s-%s-%d" % (ancestor, productName, level)
                    if listedName in listedBoM[fatherRef]:
                        listedline = listedBoM[fatherRef][listedName]
                        product = listedline['product']
                        quantity = QuantityInBom(listedBoM, product.name)
                        res['name'] = product.name
                        res['item'] = l.itemnum
                        res['pfather'] = fatherName
                        res['pname'] = product.name
                        res['pdesc'] = _(product.description)
                        res['pcode'] = l.product_id.default_code
                        res['previ'] = product.engineering_revision
                        res['pqty'] = quantity
                        res['uname'] = l.product_uom.name
                        res['pweight'] = product.weight
                        res['code'] = l.product_id.default_code
                        res['level'] = level
                        res['prodBrws'] = l.product_id
                        res['prodTmplBrws'] = product
                        tmp_result.append(res)
                        for bomId in l.product_id.bom_ids:
                            if bomId.type == l.bom_id.type:
                                if bomId.bom_line_ids:
                                    buffer_obj = _get_rec(bomId.bom_line_ids, listedBoM, listed, level + 1, fatherName)
                                    tmp_result.extend(buffer_obj)
            return tmp_result

        results = SummarizeBom(myObject, level + 1, results)
        result.extend(_get_rec(myObject, results, listed, level + 1))

        return result

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
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
