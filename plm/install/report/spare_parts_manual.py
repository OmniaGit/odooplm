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
import base64
import time

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle,Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from operator import itemgetter
from book_collector import BookCollector
from pyPdf import PdfFileWriter, PdfFileReader

from openerp.report.render import render
from openerp.report.interface import report_int
from openerp.report import report_sxw
from openerp import pooler

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

def _customPath():
    return os.path.join(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),'custom'),'report')
customModulePath=_customPath()


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

header_file=os.path.join(customModulePath,"spare_parts_header.rml")
if not os.path.exists(header_file):
    header_file=os.path.join(openerpModulePath,"spare_parts_header.rml")

body_file=os.path.join(customModulePath,"spare_parts_body.rml")
if not os.path.exists(body_file):
    body_file=os.path.join(openerpModulePath,"spare_parts_body.rml")

def isPdf(fileName):
    if (os.path.splitext(fileName)[1].lower()=='.pdf'):
        return True
    return False

def getDocumentStream(docRepository,objDoc):
    """ 
        Gets the stream of a file
    """ 
    content=False
    try:
        if (not objDoc.store_fname) and (objDoc.db_datas):
            content = base64.decodestring(objDoc.db_datas)
        else:
            content = file(os.path.join(docRepository, objDoc.store_fname), 'rb').read()
    except Exception, ex:
        print "getFileStream : Exception (%s)reading  stream on file : %s." %(str(ex),objDoc.datas_fname)
    return content


class bom_structure_one_sum_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_one_sum_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children':self.get_children,
            'bom_type':self.bom_type,
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
                product=l.product_id.product_tmpl_id
                if product.name in listed.keys():
                    res=tmp_result[listed[product.name]]
                    res['pqty']=res['pqty']+l.product_qty
                    tmp_result[listed[product.name]]=res
                else:
                    res['name']=product.name
                    res['item']=l.itemnum
                    res['pname']=l.product_id.name
                    res['pdesc']=product.description
                    res['pcode']=l.product_id.default_code
                    res['previ']=product.engineering_revision
                    res['pqty']=l.product_qty
                    res['uname']=l.product_uom.name
                    res['pweight']=product.weight_net
                    res['code']=l.product_id.default_code
                    res['level']=level
                    tmp_result.append(res)
                    listed[product.name]=keyIndex
                    keyIndex+=1
            return result.extend(tmp_result)

        children=_get_rec(object,level+1)

        return result

    def bom_type(self, object):
        result=dict(self.pool.get(object._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(object.type,'')
        return _(result)

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
        recursion=True
        if self._report_int__name== 'report.product.product.spare.parts.pdf.one':
            recursion=False
        self.processedObjs=[]
        self.pool = pooler.get_pool(cr.dbname)
        componentType=self.pool.get('product.product')
        bomType=self.pool.get('mrp.bom')
        userType=self.pool.get('res.users')
        user=userType.browse(cr, uid, uid, context=context)
        msg = "Printed by "+str(user.name)+" : "+ str(time.strftime("%d/%m/%Y %H:%M:%S"))
        output = BookCollector(customTest=(True,msg))
        components=componentType.browse(cr, uid, ids, context=context)
        for component in components:
            self.processedObjs=[]
            buf=self.getFirstPage(cr, uid, [component.id],context)
            output.addPage(buf)
            self.getSparePartsPdfFile(cr, uid, context, component, output, componentType, bomType,recursion)
        if output != None:
            pdf_string = StringIO.StringIO()
            output.collector.write(pdf_string)
            self.obj = external_pdf(pdf_string.getvalue())
            self.obj.render()
            pdf_string.close()
            return (self.obj.pdf, 'pdf')
        return (False, '')    
   
    def getSparePartsPdfFile(self, cr, uid, context, product, output, componentTemplate, bomTemplate,recursion):
        packedObjs=[]
        packedIds=[]
        if product in self.processedObjs:
            return
        bomIds=bomTemplate.search(cr,uid,[('product_id','=',product.id),('type','=','spbom')])
        if len(bomIds)<1:
            bomIds=bomTemplate.search(cr,uid,[('product_tmpl_id','=',product.product_tmpl_id.id),('type','=','spbom')])
#        if len(bomIds)<1:
#            bomIds=bomTemplate.search(cr,uid,[('product_tmpl_id','=',product.id),('type','=','normal')])
#        if len(bomIds)<1:
#            bomIds=bomTemplate.search(cr,uid,[('product_tmpl_id','=',product.id),('type','=','ebom')])
        if len(bomIds)>0:
            BomObject=bomTemplate.browse(cr, uid, bomIds[0], context=context)
            if BomObject:
                self.processedObjs.append(product)
                for bom_line in BomObject.bom_line_ids:
                    packedObjs.append(bom_line.product_id)
                    packedIds.append(bom_line.id)
                if len(packedIds)>0:
                    for pageStream in self.getPdfComponentLayout(cr, product):
                        output.addPage(pageStream)
                    stream,typerep=BODY.create(cr, uid, [BomObject.id], data={'report_type': u'pdf'},context=context) 
                    pageStream=StringIO.StringIO()
                    pageStream.write(stream)
                    output.addPage(pageStream)
                    if recursion:
                        for packedObj in packedObjs:
                            if not packedObj in self.processedObjs:
                                self.getSparePartsPdfFile(cr,uid,context,packedObj,output,componentTemplate,bomTemplate,recursion)   
 
    def getPdfComponentLayout(self, cr, component):
        ret=[]
        docRepository=self.pool.get('plm.document')._get_filestore(cr)
        for document in component.linkeddocuments:
            if (document.usedforspare) and (document.type=='binary'):
                if document.printout:
                    ret.append(StringIO.StringIO(base64.decodestring(document.printout)))
                elif isPdf(document.datas_fname):
                    value=getDocumentStream(docRepository,document)
                    if value:
                        ret.append(StringIO.StringIO(value))
        return ret 
    
    def getFirstPage(self,cr, uid, ids,context):
        strbuffer = StringIO.StringIO()
        reportStream,reportType=HEADER.create(cr, uid, ids, data={'report_type': u'pdf'},context=context)
        strbuffer.write(reportStream)
        return strbuffer
          


component_spare_parts_report('report.product.product.spare.parts.pdf')

component_spare_parts_report('report.product.product.spare.parts.pdf.one')