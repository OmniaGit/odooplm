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
#
#    To customize report layout :
#
#    1 - Configure final layout using bom_structure.sxw in OpenOffice
#    2 - Compile to bom_structure.rml using ..\base_report_designer\openerp_sxw2rml\openerp_sxw2rml.py
#           python openerp_sxw2rml.py bom_structure.sxw > bom_structure.rml
#
##############################################################################
import os
import time
from operator import itemgetter

from openerp.report import report_sxw
from openerp.tools.translate import _


def _moduleName():
    path = os.path.dirname(__file__)
    return os.path.basename(os.path.dirname(os.path.dirname(path)))
openerpModule=_moduleName()

def _thisModule():
    return os.path.splitext(os.path.basename(__file__))[0]
thisModule=_thisModule()

def _translate(value):
    return _(value)

###############################################################################################################à

def _createtemplate():
    """
        Automatic XML menu creation
    """
    filepath=os.path.dirname(__file__)
    fileName=thisModule+'.xml'
    fileOut = open(os.path.join(filepath,fileName), 'w')
    
    listout=[('report_plm_bom_structure_all','BOM All Levels','plm.bom.structure.all')]
    listout.append(('report_plm_bom_structure_one','BOM One Level','plm.bom.structure.one'))
    listout.append(('report_plm_bom_structure_all_sum','BOM All Levels Summarized','plm.bom.structure.all.sum'))
    listout.append(('report_plm_bom_structure_one_sum','BOM One Level Summarized','plm.bom.structure.one.sum'))
    listout.append(('report_plm_bom_structure_leaves','BOM Only Leaves Summarized','plm.bom.structure.leaves'))
    listout.append(('report_plm_bom_structure_flat','BOM All Flat Summarized','plm.bom.structure.flat'))

    fileOut.write(u'<?xml version="1.0"?>\n<openerp>\n    <data>\n\n')
    fileOut.write(u'<!--\n       IMPORTANT : DO NOT CHANGE THIS FILE, IT WILL BE REGENERERATED AUTOMATICALLY\n-->\n\n')
  
    for label,description,name in listout:
        fileOut.write(u'        <report auto="True"\n                header="True"\n                model="mrp.bom"\n')
        fileOut.write(u'                id="%s"\n                string="%s"\n                name="%s"\n' %(label,description,name))
        fileOut.write(u'                rml="%s/install/report/%s.rml"\n' %(openerpModule, thisModule))
        fileOut.write(u'                report_type="pdf"\n                file=""\n                 />\n')
    
    fileOut.write(u'<!--\n       IMPORTANT : DO NOT CHANGE THIS FILE, IT WILL BE REGENERERATED AUTOMATICALLY\n-->\n\n')
    fileOut.write(u'    </data>\n</openerp>\n')
    fileOut.close()
_createtemplate()

###############################################################################################################à

def BomSort(myObject):
    valid=False
    bomobject=[]
    res={}
    index=0
    for l in myObject:
        res[str(index)]=l.itemnum
        index+=1
        if l.itemnum>0:
            valid=True
    if not valid:
        res={}
        index=0
        for l in myObject:
            res[str(index)]=l.product_id.product_tmpl_id.name
            index+=1
    items = res.items()
    items.sort(key = itemgetter(1))
    for res in items:
        bomobject.append(myObject[int(res[0])])
    return bomobject

def SummarizeBom(bomobject, level=1, result={}, ancestorName=""):

    for l in bomobject:
        evaluate=True
        fatherName=l.bom_id.product_id.name
        productName=l.product_id.name
        fatherRef="%s-%d" %(fatherName,level-1)
        productRef="%s-%s-%d" %(ancestorName,productName,level)
        if fatherRef in result:
            listed=result[fatherRef]
        else:
            result[fatherRef]={}
            listed={}
            
        if productRef in listed and listed[productRef]['father']==fatherName:
            res=listed[productRef]
            res['pqty']=res['pqty']+l.product_qty
            evaluate=False
        else:
            res={}
            res['product']=l.product_id
            res['name']=l.product_id.name
            res['ancestor']=ancestorName
            res['father']=fatherName
            res['pqty']=l.product_qty
            res['level']=level
            listed[productRef]=res
        
        result[fatherRef]=listed
        if evaluate:
            for bomId in l.product_id.bom_ids:
                if bomId.type == l.bom_id.type:
                    if bomId.bom_line_ids:
                        result.update(SummarizeBom(bomId.bom_line_ids, level+1, result,fatherName))
                        break

    return result

def QuantityInBom(listedBoM={}, productName=""):
    found=[]
    result=0.0
    for fatherRef in listedBoM.keys():
        if not fatherRef in found:
            for listedName in listedBoM[fatherRef]:
                listedline=listedBoM[fatherRef][listedName]
                name=listedline['name']
                if name==productName:
                    result+=listedline['pqty'] * QuantityInBom(listedBoM, listedline['father'])    
                    found.append("%s-%d" %(listedline['father'],listedline['level']))
                    break
    if not found:
        result=1.0
    return result

class bom_structure_all_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_all_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children':self.get_children,
            'bom_type':self.bom_type,
            'trans':_translate,
        })

    def get_children(self, myObject, level=0):
        result=[]

        def _get_rec(bomobject,level):
            myObject=BomSort(bomobject)

            for l in myObject:
                res={}
                product=l.product_id.product_tmpl_id
                res['name']=product.name
                res['item']=l.itemnum
                res['ancestor']=l.bom_id.product_id
                res['pname']=product.name
                res['pdesc']=_(product.description)
                res['pcode']=l.product_id.default_code
                res['previ']=product.engineering_revision
                res['pqty']=l.product_qty
                res['uname']=l.product_uom.name
                res['pweight']=product.weight_net
                res['code']=l.product_id.default_code
                res['level']=level
                result.append(res)
                for bomId in l.product_id.bom_ids:
                    if bomId.type == l.bom_id.type:
                        _get_rec(bomId.bom_line_ids,level+1)
                        break
            return result

        children=_get_rec(myObject,level+1)

        return children

    def bom_type(self, myObject):
        result=dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type,'')
        return _(result)

report_sxw.report_sxw('report.plm.bom.structure.all','mrp.bom','/'+openerpModule+'/install/report/'+thisModule+'.rml',parser=bom_structure_all_custom_report,header='internal')


class bom_structure_one_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_one_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children':self.get_children,
            'bom_type':self.bom_type,
            'trans':_translate,
        })

    def get_children(self, myObject, level=0):
        result=[]

        def _get_rec(bomobject,level):
            myObject=BomSort(bomobject)
            for l in myObject:
                res={}
                product=l.product_id.product_tmpl_id
                res['name']=product.name
                res['item']=l.itemnum
                res['pname']=product.name
                res['pdesc']=_(product.description)
                res['pcode']=l.product_id.default_code
                res['previ']=product.engineering_revision
                res['pqty']=l.product_qty
                res['uname']=l.product_uom.name
                res['pweight']=product.weight_net
                res['code']=l.product_id.default_code
                res['level']=level
                result.append(res)
            return result

        children=_get_rec(myObject,level+1)

        return children

    def bom_type(self, myObject):
        result=dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type,'')
        return _(result)

report_sxw.report_sxw('report.plm.bom.structure.one','mrp.bom','/'+openerpModule+'/install/report/'+thisModule+'.rml',parser=bom_structure_one_custom_report,header='internal')


class bom_structure_all_sum_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_all_sum_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children':self.get_children,
            'bom_type':self.bom_type,
            'trans':_translate,
        })

    def get_children(self, myObject, level=0):
        result=[]
        results={}

        def _get_rec(bomobject, listedBoM, level, ancestor=""):
            listed=[]
            myObject=BomSort(bomobject)
            tmp_result=[]
            for l in myObject:
                productName=l.product_id.name
                if productName in listed:
                    continue
                res={}
                listed.append(productName)
                fatherName=l.bom_id.product_id.name
                fatherRef="%s-%d" %(fatherName, level-1)
                if fatherRef in listedBoM.keys():
                    listedName="%s-%s-%d" %(ancestor, productName, level)
                    if listedName in listedBoM[fatherRef]:
                        listedline=listedBoM[fatherRef][listedName]
                        product=listedline['product']
                        res['name']=product.name
                        res['item']=l.itemnum
                        res['pfather']=fatherName
                        res['pname']=product.name
                        res['pdesc']=_(product.description)
                        res['pcode']=l.product_id.default_code
                        res['previ']=product.engineering_revision
                        res['pqty']=listedline['pqty']
                        res['uname']=l.product_uom.name
                        res['pweight']=product.weight_net
                        res['code']=l.product_id.default_code
                        res['level']=level
                        tmp_result.append(res)
                        
                        for bomId in l.product_id.bom_ids:
                            if bomId.type == l.bom_id.type:
                                if bomId.bom_line_ids:
                                    buffer=_get_rec(bomId.bom_line_ids,listedBoM,level+1,fatherName)
                                    tmp_result.extend(buffer)
                                    break
            return tmp_result

        results=SummarizeBom(myObject,level+1,results)
        result.extend(_get_rec(myObject,results,level+1))

        return result

    def bom_type(self, myObject):
        result=dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type,'')
        return _(result)

report_sxw.report_sxw('report.plm.bom.structure.all.sum','mrp.bom','/'+openerpModule+'/install/report/'+thisModule+'.rml',parser=bom_structure_all_sum_custom_report,header='internal')

class bom_structure_one_sum_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_one_sum_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children':self.get_children,
            'bom_type':self.bom_type,
            'trans':_translate,
        })

    def get_children(self, myObject, level=0):
        result=[]

        def _get_rec(bomobject,level):
            myObject=BomSort(bomobject)
            tmp_result=[]
            listed={}
            keyIndex=0
            for l in myObject:
                res={}
                product=l.product_id.product_tmpl_id
                if product.name in listed.keys():
                    res=tmp_result[listed[product.name]]
                    res['pqty']=res['pqty']+l.product_qty
                    tmp_result[listed[product.name]]=res
                else:
                    res['name']=product.name
                    res['item']=l.itemnum
                    res['pname']=product.name
                    res['pdesc']=_(product.description)
                    res['pcode']=l.product_id.default_code
                    res['previ']=product.engineering_revision
                    res['pqty']=l.product_qty
                    res['uname']=l.product_uom.name
                    res['pweight']=product.weight_net
                    res['code']=l.product_id.default_code
                    res['level']=level
                    tmp_result.append(res)
                    listed[l.product_id.name]=keyIndex
                    keyIndex+=1
            return result.extend(tmp_result)

        children=_get_rec(myObject,level+1)

        return result

    def bom_type(self, myObject):
        result=dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type,'')
        return _(result)

report_sxw.report_sxw('report.plm.bom.structure.one.sum','mrp.bom','/'+openerpModule+'/install/report/'+thisModule+'.rml',parser=bom_structure_one_sum_custom_report,header='internal')

class bom_structure_leaves_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_leaves_custom_report, self).__init__(cr, uid, name, context=context)
        self.keyIndex=0
        self.localcontext.update({
            'time': time,
            'get_children':self.get_children,
            'bom_type':self.bom_type,
            'trans':_translate,
        })

    def get_children(self, myObject, level=0):
        result=[]
        results={}
        listed=[]

        def _get_rec(bomobject, listedBoM, listed, level, ancestor=""):
            
            myObject=BomSort(bomobject)
            tmp_result=[]
            for l in myObject:
                productName=l.product_id.name
                if productName in listed:
                    continue
                res={}
                listed.append(productName)
                fatherName=l.bom_id.product_id.name
                fatherRef="%s-%d" %(fatherName, level-1)
                if fatherRef in listedBoM.keys():
                    listedName="%s-%s-%d" %(ancestor, productName, level)
                    if listedName in listedBoM[fatherRef]:
                        listedline=listedBoM[fatherRef][listedName]
                        product=listedline['product']
                        productRef="%s-%d" %(product.name, level)
                        if not productRef in listedBoM.keys():
                            quantity=QuantityInBom(listedBoM, product.name)
                            res['name']=product.name
                            res['item']=l.itemnum
                            res['pfather']=fatherName
                            res['pname']=product.name
                            res['pdesc']=_(product.description)
                            res['pcode']=l.product_id.default_code
                            res['previ']=product.engineering_revision
                            res['pqty']=quantity
                            res['uname']=l.product_uom.name
                            res['pweight']=product.weight_net
                            res['code']=l.product_id.default_code
                            res['level']=level
                            tmp_result.append(res)
                        
                        for bomId in l.product_id.bom_ids:
                            if bomId.type == l.bom_id.type:
                                if bomId.bom_line_ids:
                                    buffer=_get_rec(bomId.bom_line_ids,listedBoM,listed,level+1,fatherName)
                                    tmp_result.extend(buffer)
                                    break
            return tmp_result

        results=SummarizeBom(myObject,level+1,results)
        result.extend(_get_rec(myObject,results,listed,level+1))

        return result

    def bom_type(self, myObject):
        result=dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type,'')
        return _(result)

report_sxw.report_sxw('report.plm.bom.structure.leaves','mrp.bom','/'+openerpModule+'/install/report/'+thisModule+'.rml',parser=bom_structure_leaves_custom_report,header='internal')

class bom_structure_flat_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_flat_custom_report, self).__init__(cr, uid, name, context=context)
        self.keyIndex=0
        self.localcontext.update({
            'time': time,
            'get_children':self.get_children,
            'bom_type':self.bom_type,
            'trans':_translate,
        })

    def get_children(self, myObject, level=0):
        result=[]
        results={}
        listed=[]

        def _get_rec(bomobject, listedBoM, listed, level, ancestor=""):
            
            myObject=BomSort(bomobject)
            tmp_result=[]
            for l in myObject:
                productName=l.product_id.name
                if productName in listed:
                    continue
                res={}
                listed.append(productName)
                fatherName=l.bom_id.product_id.name
                fatherRef="%s-%d" %(fatherName, level-1)
                if fatherRef in listedBoM.keys():
                    listedName="%s-%s-%d" %(ancestor, productName, level)
                    if listedName in listedBoM[fatherRef]:
                        listedline=listedBoM[fatherRef][listedName]
                        product=listedline['product']
                        quantity=QuantityInBom(listedBoM, product.name)
                        res['name']=product.name
                        res['item']=l.itemnum
                        res['pfather']=fatherName
                        res['pname']=product.name
                        res['pdesc']=_(product.description)
                        res['pcode']=l.product_id.default_code
                        res['previ']=product.engineering_revision
                        res['pqty']=quantity
                        res['uname']=l.product_uom.name
                        res['pweight']=product.weight_net
                        res['code']=l.product_id.default_code
                        res['level']=level
                        tmp_result.append(res)
                        
                        for bomId in l.product_id.bom_ids:
                            if bomId.type == l.bom_id.type:
                                if bomId.bom_line_ids:
                                    buffer=_get_rec(bomId.bom_line_ids,listedBoM,listed,level+1,fatherName)
                                    tmp_result.extend(buffer)
                                    break
            return tmp_result

        results=SummarizeBom(myObject,level+1,results)
        result.extend(_get_rec(myObject,results,listed,level+1))

        return result
        
    def bom_type(self, myObject):
        result=dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type,'')
        return _(result)

report_sxw.report_sxw('report.plm.bom.structure.flat','mrp.bom','/'+openerpModule+'/install/report/'+thisModule+'.rml',parser=bom_structure_flat_custom_report,header='internal')
