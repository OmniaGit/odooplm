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

"""
Created on Apr 14, 2016

@author: Daniel Smerghetto
"""

from odoo import api
from odoo import models
from operator import itemgetter
from odoo import _
import odoo
import time
import logging


def _translate(value):
    return _(value)


def get_bom_report(myObject, recursion=False, flat=False, leaf=False, level=1, summarize=False):
    def getBom(bomLineObj):
        newBom = None
        for bomBws in bomLineObj.related_bom_ids:
            if bomBws.type == bomLineObj.type:
                newBom = bomBws
                break
        return newBom

    def get_out_line_infos(bomLineBrws, productTmplBrws, prodQty):
        res = {
            'row_bom_line': bomLineBrws,
            'name': productTmplBrws.engineering_code,
            'item': bomLineBrws.itemnum,
            'pname': productTmplBrws.engineering_code,
            'pdesc': _(productTmplBrws.name),
            'pcode': bomLineBrws.product_id.default_code,
            'previ': productTmplBrws.engineering_revision,
            'pqty': prodQty,
            'uname': bomLineBrws.product_uom_id.name,
            'pweight': productTmplBrws.weight,
            'code': bomLineBrws.product_id.default_code,
            'level': level,
            'prodBrws': bomLineBrws.product_id,
            'prodTmplBrws': productTmplBrws,
            'lineBrws': bomLineBrws
        }
        return res

    def leafComputeRecursion(bomObj, parentQty=1):
        for l in bomObj.bom_line_ids:
            lineQty = l.product_qty
            productTmplObj = l.product_id.product_tmpl_id
            prodTmlId = productTmplObj.id
            prodQty = parentQty * lineQty
            myNewBom = getBom(l)
            if myNewBom:
                leafComputeRecursion(myNewBom, prodQty)
            else:
                if prodTmlId not in list(leafRes.keys()):
                    resDict = get_out_line_infos(l, productTmplObj, prodQty)
                    resDict['engineering_code'] = productTmplObj.engineering_code
                    resDict['level'] = ''
                    leafRes[prodTmlId] = resDict
                else:
                    leafRes[prodTmlId]['pqty'] = leafRes[prodTmlId]['pqty'] + prodQty

    if leaf:
        leafRes = {}
        leafComputeRecursion(myObject)
        return list(leafRes.values())

    def summarize_level(bomObj, recursion=False, flat=False, level=1, summarize=False, parentQty=1):
        def updateQty(tmplId, qtyToAdd):
            for localIndex, valsList in list(orderDict.items()):
                count = 0
                for res in valsList:
                    tmplBrws = res.get('prodTmplBrws', False)
                    if not tmplBrws:
                        logging.error('Template browse not found printing bom: %r' % (res))
                        continue
                    if tmplBrws.id == tmplId:
                        newQty = orderDict[localIndex][count]['pqty'] + qtyToAdd
                        orderDict[localIndex][count]['pqty'] = newQty
                        return
                    count = count + 1

        orderDict = {}
        levelListed = []
        for l in bomObj.bom_line_ids:
            index = l.itemnum
            if index not in list(orderDict.keys()):
                orderDict[index] = []
            children = {}
            productTmplObj = l.product_id.product_tmpl_id
            prodTmlId = productTmplObj.id
            if recursion or flat:
                myNewBom = getBom(l)
                if myNewBom:
                    children = summarize_level(myNewBom, recursion, flat, level + 1, summarize,
                                               l.product_qty * parentQty)
            if prodTmlId in levelListed and summarize:
                qty = l.product_qty
                updateQty(prodTmlId, qty)
            else:
                prodQty = l.product_qty
                res = get_out_line_infos(l, productTmplObj, prodQty)
                res['engineering_code'] = (bomObj.env['ir.config_parameter'].get_param(
                    'REPORT_INDENTATION_KEY') or '') * level + ' ' + (productTmplObj.engineering_code or '')
                res['children'] = children
                res['level'] = level
                levelListed.append(prodTmlId)
                orderDict[index].append(res)
        return orderDict

    out = []

    def getOutList(outDict, parentQty=1):
        itemNums = list(outDict.keys())
        itemNums.sort()
        for itemNum in itemNums:
            valsDict = outDict.get(itemNum, {})
            for valDict in valsDict:
                children = valDict.get('children', {}).copy()
                localQty = valDict['pqty']
                if flat:
                    localQty = localQty * parentQty
                    valDict['pqty'] = localQty
                del valDict['children']
                out.append(valDict)
                getOutList(children, localQty)

    outDict = summarize_level(myObject, recursion, flat, level, summarize)
    getOutList(outDict)
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
    items = list(res.items())
    items.sort(key=itemgetter(1))
    for res in items:
        bomobject.append(myObject[int(res[0])])
    return bomobject


class ReportBomStructureAll(models.AbstractModel):
    _name = 'report.plm.bom_structure_all'
    _description = "Report Bom All Structure"

    def get_children(self, myObject, level=0):
        return get_bom_report(myObject, recursion=True, flat=False, leaf=False, level=1, summarize=False)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        return {'docs': boms,
                'bom_type': self.bom_type,
                'get_children': self.get_children}


class ReportBomStructureOne(models.AbstractModel):
    _name = 'report.plm.bom_structure_one'
    _description = 'Report PLM Bom Structure'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('plm.bom_structure_one')
        docargs = {
            'doc_model': report.model,
            'docs': self,
            'data': data,
            'doc_ids': docids}
        return report_obj.render('plm.bom_structure_one', docargs)

    def get_children(self, myObject, level=0):
        return get_bom_report(myObject, recursion=False, flat=False, leaf=False, level=1, summarize=False)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        return {'docs': boms,
                'bom_type': self.bom_type,
                'get_children': self.get_children}


class ReportBomStructureAllSum(models.AbstractModel):
    _name = 'report.plm.bom_structure_all_sum'
    _description = "Report Bom All Structure summarised"

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('plm.bom_structure_all_sum')
        docargs = {
            'doc_model': report.model,
            'docs': self,
            'data': data,
            'doc_ids': docids}
        return report_obj.render('plm.bom_structure_all_sum', docargs)

    def get_children(self, myObject, level=1):
        return get_bom_report(myObject, recursion=True, flat=False, leaf=False, level=level, summarize=True)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        return {'docs': boms,
                'bom_type': self.bom_type,
                'get_children': self.get_children}


class ReportBomStructureOneSum(models.AbstractModel):
    _name = 'report.plm.bom_structure_one_sum'
    _description = 'Report PLM Bom Structure summaraized'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('plm.bom_structure_one_sum')
        docargs = {
            'doc_model': report.model,
            'docs': self,
            'data': data,
            'doc_ids': docids}
        return report_obj.render('plm.bom_structure_one_sum', docargs)

    def get_children(self, myObject):
        return get_bom_report(myObject, summarize=True)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        return {'docs': boms,
                'bom_type': self.bom_type,
                'get_children': self.get_children}


class ReportBomStructureLevels(models.AbstractModel):
    _name = 'report.plm.bom_structure_leaves'
    _description = 'Report Bom Leavs'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('plm.bom_structure_leaves')
        docargs = {
            'doc_model': report.model,
            'docs': self,
            'data': data,
            'doc_ids': docids}
        return report_obj.render('plm.bom_structure_leaves', docargs)

    def get_children(self, myObject, level=1):
        return get_bom_report(myObject, leaf=True, level=level, summarize=True)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        return {'docs': boms,
                'bom_type': self.bom_type,
                'get_children': self.get_children}


class ReportBomStructureFlat(models.AbstractModel):
    _name = 'report.plm.bom_structure_flat'
    _description = 'Report Bom Structure'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('plm.bom_structure_flat')
        docargs = {
            'doc_model': report.model,
            'docs': self,
            'data': data,
            'doc_ids': docids}
        return report_obj.render('plm.bom_structure_flat', docargs)

    def get_children(self, myObject, level=1):
        return get_bom_report(myObject, recursion=True, flat=True, leaf=False, level=level, summarize=True)

    def bom_type(self, myObject):
        result = dict(myObject.fields_get()['type']['selection']).get(myObject.type, '')
        return _(result)

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        return {'docs': boms,
                'bom_type': self.bom_type,
                'get_children': self.get_children}
