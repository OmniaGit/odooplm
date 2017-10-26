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
from operator import itemgetter
from odoo import _
import odoo
from odoo import api
from odoo import models
from odoo.addons.plm.report.book_collector import BookCollector
from odoo.addons.plm.report.book_collector import getBottomMessage

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
from io import BytesIO
import base64
import os
import logging
from datetime import datetime
from dateutil import tz


from PyPDF2 import PdfFileWriter
from PyPDF2 import PdfFileReader


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
            content = base64.b64decode(objDoc.db_datas)
        else:
            with open(os.path.join(docRepository, objDoc.store_fname), 'rb') as f:
                content = f.read()
    except Exception as ex:
        logging.error("getFileStream : Exception (%s)reading  stream on file : %s." % (ex, objDoc.datas_fname))
    return content


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


class report_spare_parts_header(models.AbstractModel):
    _name = 'report.plm_spare.bom_spare_header'

    def get_document_brws(self, objProduct):
        oldest_obj = None
        oldest_dt = None
        if objProduct:
            for linkedBrwsDoc in objProduct.linkeddocuments:
                create_date_str = linkedBrwsDoc.create_date
                create_date = datetime.strptime(create_date_str, DEFAULT_SERVER_DATETIME_FORMAT)
                if oldest_dt is None or create_date < oldest_dt:
                    oldest_dt = create_date
                    oldest_obj = linkedBrwsDoc
        return oldest_obj

    def get_report_values(self, docids, data=None):
        products = self.env['product.product'].browse(docids)
        return {'docs': products,
                'time': time,
                'get_document_brws': self.get_document_brws}


class ReportSpareDocumentOne(models.AbstractModel):
    _name = 'report.plm_spare.pdf_one'
    """
    Calculates the bom structure spare parts manual
    """

    @api.model
    def create(self, components):
        recursion = True
        if ReportSpareDocumentOne._name == 'report.plm_spare.pdf_one':
            recursion = False
        self.processedObjs = []

        componentType = self.env['product.product']
        bomType = self.env['mrp.bom']
        user = self.env['res.users'].browse(self.env.uid)
        msg = getBottomMessage(user, self.env.context)
        mainBookCollector = BookCollector(customTest=(True, msg))
        for component in components:
            self.processedObjs = []
            buf = self.getFirstPage([component.id])
            mainBookCollector.addPage((buf, ''))
            self.getSparePartsPdfFile(component, mainBookCollector, componentType, bomType, recursion)
        if mainBookCollector is not None:
            pdf_string = BytesIO()
            mainBookCollector.collector.write(pdf_string)
            out = pdf_string.getvalue()
            pdf_string.close()
            byteString = b"data:application/pdf;base64," + base64.b64encode(out)
            return byteString.decode('UTF-8')
        logging.warning('Unable to create PDF')
        return (False, '')

    def getSparePartsPdfFile(self, product, output, componentTemplate, bomTemplate, recursion):
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
                    for pageStream in self.getPdfComponentLayout(product):
                        try:
                            output.addPage((pageStream, ''))
                        except Exception as ex:
                            logging.error(ex)
                            raise ex
                    pdf = self.env.ref('plm.report_plm_bom_structure_one').sudo().render_qweb_pdf(bomBrwsIds.ids)[0]
                    pageStream = BytesIO()
                    pageStream.write(pdf)
                    output.addPage((pageStream, ''))
                    if recursion:
                        for packedObj in packedObjs:
                            if packedObj not in self.processedObjs:
                                self.getSparePartsPdfFile(packedObj, output, componentTemplate, bomTemplate, recursion)

    def getPdfComponentLayout(self, component):
        ret = []
        docRepository = self.env['plm.document']._get_filestore()
        for document in component.linkeddocuments:
            if (document.usedforspare) and (document.type == 'binary'):
                if document.printout and str(document.printout) != 'None':
                    ret.append(BytesIO(base64.b64decode(document.printout)))
                elif isPdf(document.datas_fname):
                    value = getDocumentStream(docRepository, document)
                    if value:
                        ret.append(BytesIO(value))
        return ret

    def getFirstPage(self, ids):
        strbuffer = BytesIO()
        # todo: si rompe qui con v11 .. capire come fare il report da codice 
        pdf = self.env.ref('plm_spare.report_product_product_spare_header').sudo().render_qweb_pdf(ids)[0]
        strbuffer.write(pdf)
        return strbuffer

    @api.model
    def get_report_values(self, docids, data=None):
        documents = self.env['product.product'].browse(docids)
        return {'docs': documents,
                'get_content': self.create}


class ReportSpareDocumentAll(ReportSpareDocumentOne):
    _name = 'report.plm_spare.pdf_all'
