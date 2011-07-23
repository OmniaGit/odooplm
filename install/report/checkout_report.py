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
from report.render import render
from report.interface import report_int

# NOTE : TO BE ADDED TO FINAL CONFIGURATION. NOT IN STANDARD PYTHON
from pyPdf import PdfFileWriter, PdfFileReader
# NOTE : TO BE ADDED TO FINAL CONFIGURATION. NOT IN STANDARD PYTHON

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
        output = None
        children=[]
        packed=[]
        checkouts=checkoutType.browse(cr, uid, ids)
        for checkout in checkouts:
            document=checkout.documentid
            if document.printout:
                if not document.id in packed:   
                    if output == None:
                        output = PdfFileWriter()
                    input1 = PdfFileReader(StringIO.StringIO(base64.decodestring(document.printout)))
                    output.addPage(input1.getPage(0))
                    packed.append(document.id)
        if output != None:
            pdf_string = StringIO.StringIO()
            output.write(pdf_string)
            self.obj = external_pdf(pdf_string.getvalue())
            self.obj.render()
            pdf_string.close()
            return (self.obj.pdf, 'pdf')
        return (False, '')

checkout_custom_report('report.plm.checkout.pdf')