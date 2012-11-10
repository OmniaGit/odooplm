 # -*- coding: utf-8 -*-
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
import StringIO
import os
import random
import string
import pooler
import base64
import time
from report.render import render
from report.interface import report_int
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle,Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from report import report_sxw
from operator import itemgetter

# NOTE : TO BE ADDED TO FINAL CONFIGURATION. NOT IN STANDARD PYTHON
from pyPdf import PdfFileWriter, PdfFileReader
# NOTE : TO BE ADDED TO FINAL CONFIGURATION. NOT IN STANDARD PYTHON
from book_collector import BookCollector
#constant
FIRST_LEVEL=0
BOM_SHOW_FIELDS=['Position','Code','Description','Quantity']

def PageCellHeader(text):
    styleSheet = getSampleStyleSheet()
    ss=styleSheet["BodyText"]
    ss.fontSize=20
    ss.spaceAfter=20
    ss.leading=22
    p = Paragraph("""
    <para align=center spaceb=3>
    """
    +
    str(text)
    +
    """
    </para>
    """,ss
    )
    return p

def TableHeader(text):
    styleSheet = getSampleStyleSheet()
    ss=styleSheet["BodyText"]
    #ss.backColor="#2D9AED"
    p = Paragraph("""
    <para align=center spaceb=3>
    <b>
    """
    +
    str(text)
    +
    """
    </b>
    </para>
    """,ss
    )
    return p

def TableCell(text):
    styleSheet = getSampleStyleSheet()
    p = Paragraph("""
    <para align=center spaceb=3>
    """
    +
    str(text)
    +
    """
    </para>
    """,
    styleSheet["BodyText"])
    return p

def getBomRow(objRel):
    ret=[
         TableCell(objRel.itemnum),
         TableCell(objRel.product_id.name),
         TableCell(objRel.product_id.description),
         TableCell(objRel.product_qty)
         ]
    return ret

def _moduleName():
    path = os.path.dirname(__file__)
    return os.path.basename(os.path.dirname(os.path.dirname(path)))
openerpModule=_moduleName()

def _modulePath():
    return os.path.dirname(__file__)
openerpModulePath=_modulePath()


def BomSort(object):
    bomobject=[]
    res={}
    index=0
    for l in object:
        res[str(index)]=l.itemnum
        index+=1
    items = res.items()
    items.sort(key = itemgetter(1))
    for res in items:
        bomobject.append(object[int(res[0])])
    return bomobject


class external_pdf(render):
    """ Generate External PDF """
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type = 'pdf'

    def _render(self):
        return self.pdf

header_file=os.path.join(openerpModulePath,"spare_parts_header.rml")
body_file=os.path.join(openerpModulePath,"spare_parts_body.rml")


class bom_structure_one_sum_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_one_sum_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children':self.get_children,
        })

    def get_children(self, object, level=0):
        result=[]

        def _get_rec(bomobject,level):
            object=BomSort(bomobject)
            tmp_result=[]
            listed={}
            keyIndex=0
            for l in object:
                res={}
                if l.name in listed.keys():
                    res=tmp_result[listed[l.name]]
                    res['pqty']=res['pqty']+l.product_qty
                    tmp_result[listed[l.name]]=res
                else:
                    res['name']=l.name
                    res['item']=l.itemnum
                    res['pname']=l.product_id.name
                    res['pdesc']=l.product_id.description
                    res['pcode']=l.product_id.default_code
                    res['previ']=l.product_id.engineering_revision
                    res['pqty']=l.product_qty
                    res['uname']=l.product_uom.name
                    res['pweight']=l.product_id.weight_net
                    res['code']=l.code
                    res['level']=level
                    tmp_result.append(res)
                    listed[l.name]=keyIndex
                    keyIndex+=1
            return result.extend(tmp_result)

        children=_get_rec(object,level+1)

        return result

HEADER=report_sxw.report_sxw("report.spare.parts.header", 
                            "product.product", 
                            rml=header_file,
                            header='internal')
   
BODY=report_sxw.report_sxw("report.spare.parts.body", 
                           "mrp.bom", 
                           rml=body_file,
                           parser=bom_structure_one_sum_custom_report,
                           header='internal')

class component_spare_parts_report(report_int):
    """
        Calculates the bom structure spare parts manual
    """
    
    def create(self, cr, uid, ids, datas, context=None):
        self.pool = pooler.get_pool(cr.dbname)
        componentType=self.pool.get('product.product')
        bomType=self.pool.get('mrp.bom')
        userType=self.pool.get('res.users')
        user=userType.browse(cr, uid, uid, context=context)
        msg = "Printed by "+str(user.name)+" : "+ str(time.strftime("%d/%m/%Y %H:%M:%S"))
        output = BookCollector(customTest=(True,msg))
        components=componentType.browse(cr, uid, ids, context=context)
        for component in components:
            buf=self.getFirstPage(cr, uid, [component.id],context)
            output.addPage(buf)
            self.getSparePartsPdfFile(cr, uid, context, component, output, componentType, bomType)
        if output != None:
            pdf_string = StringIO.StringIO()
            output.collector.write(pdf_string)
            self.obj = external_pdf(pdf_string.getvalue())
            self.obj.render()
            pdf_string.close()
            return (self.obj.pdf, 'pdf')
        return (False, '')    
   
    def getSparePartsPdfFile(self, cr, uid, context, component, output, componentTemplate, bomTemplate):
        packedObjs=[]
        packedIds=[]
        bomIds=bomTemplate.search(cr,uid,[('product_id','=',component.id),('type','=','spbom')])
#        if len(bomIds)<1:
#            bomIds=bomTemplate.search(cr,uid,[('product_id','=',component.id),('type','=','normal')])
#        if len(bomIds)<1:
#            bomIds=bomTemplate.search(cr,uid,[('product_id','=',component.id),('type','=','ebom')])
        if len(bomIds)>0:
            BomObject=bomTemplate.browse(cr, uid, bomIds[0], context=context)
            if BomObject:
                for bom_line in BomObject.bom_lines:
                    packedObjs.append(bom_line.product_id)
                    packedIds.append(bom_line.id)
                if len(packedIds)>0:
                    for pageStream in self.getPdfComponentLayout(component):
                        output.addPage(pageStream)
                    stream,typerep=BODY.create(cr, uid, [BomObject.id], data={'report_type': u'pdf'},context=context) 
                    pageStream=StringIO.StringIO()
                    pageStream.write(stream)
                    output.addPage(pageStream)
                    processed=[]
                    for packedObj in packedObjs:
                        if not packedObj.id in processed:
                            self.getSparePartsPdfFile(cr,uid,context,packedObj,output,componentTemplate,bomTemplate)   
                    processed.append(packedObj.id) 

    def getPdfComponentLayout(self,component):
        ret=[]
        for document in component.linkeddocuments:
            if document.printout: # and document.name[0]=='L':
                #TODO: To Evaluate document type 
                ret.append( StringIO.StringIO(base64.decodestring(document.printout)))
        return ret 
    
    def getFirstPage(self,cr, uid, ids,context):
        strbuffer = StringIO.StringIO()
        reportStream,reportType=HEADER.create(cr, uid, ids, data={'report_type': u'pdf'},context=context)
        strbuffer.write(reportStream)
        return strbuffer
          


component_spare_parts_report('report.product.product.spare.parts.pdf')