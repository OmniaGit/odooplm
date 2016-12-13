#  -*- coding: utf-8 -*-
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

from odoo.osv import osv
from odoo.report import report_sxw
from odoo.report.interface import report_int
from operator import itemgetter
from odoo import _
import odoo
from odoo.addons.plm.report.book_collector import BookCollector
from odoo.report.render import render
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
import StringIO
import base64
import os
import logging
from datetime import datetime
from dateutil import tz

try:
    from PyPDF2 import PdfFileWriter
    from PyPDF2 import PdfFileReader
except:
    logging.warning("PyPDF2 not installed ")
    from pyPdf import PdfFileWriter
    from pyPdf import PdfFileReader


def isPdf(fileName):
    if (os.path.splitext(fileName)[1].lower() == '.pdf'):
        return True
    return False


def getDocumentStream(docRepository, objDoc):
    """
        Gets the stream of a file
    """
    content = False
    try:
        if (not objDoc.store_fname) and (objDoc.db_datas):
            content = base64.decodestring(objDoc.db_datas)
        else:
            content = file(os.path.join(docRepository, objDoc.store_fname), 'rb').read()
    except Exception, ex:
        print "getFileStream : Exception (%s)reading  stream on file : %s." % (str(ex), objDoc.datas_fname)
    return content


class external_pdf(render):
    """ Generate External PDF """
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type = 'pdf'

    def _render(self):
        return self.pdf


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
    return [myObject.product_tmpl_id.name,
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


def getBottomMessage(user, context):
        to_zone = tz.gettz(context.get('tz', 'Europe/Rome'))
        from_zone = tz.tzutc()
        dt = datetime.now()
        dt = dt.replace(tzinfo=from_zone)
        localDT = dt.astimezone(to_zone)
        localDT = localDT.replace(microsecond=0)
        return "Printed by " + str(user.name) + " : " + str(localDT.ctime())


class bom_structure_one_sum_custom_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_one_sum_custom_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_children': self.get_children,
            'bom_type': self.bom_type,
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
                    res['pname'] = l.product_id.name
                    res['pdesc'] = product.description
                    res['pcode'] = l.product_id.default_code
                    res['previ'] = product.engineering_revision
                    res['pqty'] = l.product_qty
                    res['uname'] = l.product_uom_id.name
                    res['pweight'] = product.weight
                    res['code'] = l.product_id.default_code
                    res['level'] = level
                    tmp_result.append(res)
                    listed[product.name] = keyIndex
                    keyIndex += 1
            return result.extend(tmp_result)

        _get_rec(myObject, level + 1)

        return result

    def bom_type(self, myObject):
        result = dict(self.pool.get(myObject._model._name).fields_get(self.cr, self.uid)['type']['selection']).get(myObject.type, '')
        return _(result)


class bom_spare_header(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_spare_header, self).__init__(cr, uid, name, context=context)
        self.cr = cr
        self.uid = uid
        self.env = odoo.api.Environment(cr, uid, context or {})
        self.context = context
        self.localcontext.update({
            'time': time,
            'get_component_brws': self.get_component_brws,
            'get_document_brws': self.get_document_brws,
        })

    def get_component_brws(self):
        # self.pool = pooler.get_pool(self.cr.dbname)
        # FIXME: odoo removed pooler fix me
        component_ids = self.context.get('active_ids', [])
        for compBrws in self.env['product.product'].browse(component_ids):
            return compBrws
        return ''

    def get_document_brws(self):
        productBrws = self.get_component_brws()
        oldest_dt = datetime.now()
        oldest_obj = None
        for linkedBrwsDoc in productBrws.linkeddocuments:
            create_date_str = linkedBrwsDoc.create_date
            create_date = datetime.strptime(create_date_str, DEFAULT_SERVER_DATETIME_FORMAT)
            if create_date < oldest_dt:
                oldest_dt = create_date
                oldest_obj = linkedBrwsDoc
        return oldest_obj


class report_spare_parts_header(osv.AbstractModel):
    _name = 'report.plm_spare.bom_spare_header'
    _inherit = 'report.abstract_report'
    _template = 'plm_spare.bom_spare_header'
    _wrapped_report_class = bom_spare_header


class component_spare_parts_report(report_int):
    """
        Calculates the bom structure spare parts manual
    """
    def create(self, cr, uid, ids, datas, context=None):
        recursion = True
        if self._report_int__name == 'report.product.product.spare.parts.pdf.one':
            recursion = False
        self.processedObjs = []
        self.env = odoo.api.Environment(cr, uid, context or {})
        componentType = self.env['product.product']
        bomType = self.env['mrp.bom']
        user = self.env['res.users'].browse(uid)
        msg = getBottomMessage(user, context)
        output = BookCollector(customTest=(True, msg))
        components = componentType.browse(ids)
        for component in components:
            self.processedObjs = []
            buf = self.getFirstPage(cr, uid, [component.id], context)
            output.addPage((buf, ''))
            self.getSparePartsPdfFile(cr, uid, context, component, output, componentType, bomType, recursion)
        if output is not None:
            pdf_string = StringIO.StringIO()
            output.collector.write(pdf_string)
            self.obj = external_pdf(pdf_string.getvalue())
            self.obj.render()
            pdf_string.close()
            return (self.obj.pdf, 'pdf')
        logging.warning('Unable to create PDF')
        return (False, '')

    def getSparePartsPdfFile(self, cr, uid, context, product, output, componentTemplate, bomTemplate, recursion):
        packedObjs = []
        packedIds = []
        if product in self.processedObjs:
            return
        bomBrwsIds = bomTemplate.search([('product_id', '=', product.id), ('type', '=', 'spbom')])
        if len(bomBrwsIds) < 1:
            bomBrwsIds = bomTemplate.search([('product_tmpl_id', '=', product.product_tmpl_id.id), ('type', '=', 'spbom')])
        if len(bomBrwsIds) > 0:
            if bomBrwsIds:
                self.processedObjs.append(product)
                for bom_line in bomBrwsIds.bom_line_ids:
                    packedObjs.append(bom_line.product_id)
                    packedIds.append(bom_line.id)
                if len(packedIds) > 0:
                    for pageStream in self.getPdfComponentLayout(cr, product):
                        try:
                            output.addPage((pageStream, ''))
                        except Exception, ex:
                            logging.error(ex)
                            raise ex
                    context['starting_model'] = 'product.product'
                    context['active_ids'] = bomBrwsIds.ids
                    context['active_model'] = 'mrp.bom'
                    template_ids = self.env['ir.ui.view'].search([('name', '=', 'plm.bom_structure_one')])
                    pdf = self.env['report'].with_context(context).get_pdf(template_ids, 'plm.bom_structure_one')
                    pageStream = StringIO.StringIO()
                    pageStream.write(pdf)
                    output.addPage((pageStream, ''))
                    if recursion:
                        for packedObj in packedObjs:
                            if packedObj not in self.processedObjs:
                                self.getSparePartsPdfFile(cr, uid, context, packedObj, output, componentTemplate, bomTemplate, recursion)

    def getPdfComponentLayout(self, cr, component):
        ret = []
        docRepository = self.env['plm.document']._get_filestore()
        for document in component.linkeddocuments:
            if (document.usedforspare) and (document.type == 'binary'):
                if document.printout and str(document.printout) != 'None':
                    ret.append(StringIO.StringIO(base64.decodestring(document.printout)))
                elif isPdf(document.datas_fname):
                    value = getDocumentStream(docRepository, document)
                    if value:
                        ret.append(StringIO.StringIO(value))
        return ret

    def getFirstPage(self, cr, uid, ids, context):
        strbuffer = StringIO.StringIO()
        template_ids = self.env['ir.ui.view'].search([('name', '=', 'bom_spare_header')])
        context['active_ids'] = ids
        context['active_model'] = 'product.product'
        pdf = self.env['report'].get_pdf(template_ids, 'plm_spare.bom_spare_header')
        strbuffer.write(pdf)
        return strbuffer


component_spare_parts_report('report.product.product.spare.parts.pdf')


component_spare_parts_report('report.product.product.spare.parts.pdf.one')
