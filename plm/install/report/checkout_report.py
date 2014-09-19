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

from openerp.report.render import render
from openerp.report.interface import report_int
from openerp import pooler

from pyPdf import PdfFileWriter, PdfFileReader

class external_pdf(render):

    """ Generate External PDF """

    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type = 'pdf'

    def _render(self):
        return self.pdf

class checkout_custom_report(report_int):
    """
        Return a pdf report of each printable document.
    """
    def create(self, cr, uid, ids, datas, context=None):
        self.pool = pooler.get_pool(cr.dbname)
        checkoutType=self.pool.get('plm.checkout')
        output = PdfFileWriter()
        children=[]
        packed=[]
        checkouts=checkoutType.browse(cr, uid, ids)
        for checkout in checkouts:
            document=checkout.documentid
            if document.printout:
                if not document.id in packed:   
                    input1 = PdfFileReader(StringIO.StringIO(base64.decodestring(document.printout)))
                    output.addPage(input1.getPage(0))
                    packed.append(document.id)

        pdf_string = StringIO.StringIO()
        output.write(pdf_string)
        self.obj = external_pdf(pdf_string.getvalue())
        self.obj.render()
        pdf_string.close()
        return (self.obj.pdf, 'pdf')

checkout_custom_report('report.plm.checkout.pdf')