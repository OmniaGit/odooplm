##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
from .book_collector import BookCollector
from .book_collector import (packDocuments,
                             packDocumentsNew)
from datetime import datetime
from dateutil import tz
import base64
from odoo import _
from odoo import api
from odoo import models
from odoo.exceptions import UserError
from odoo.addons.plm.report.book_collector import getBottomMessage
from odoo.addons.plm.models.utils import getEmptyDocument

class ReportProductPdf(models.AbstractModel):
    _name = 'report.plm.product_pdf'
    _description = 'Report for producing pdf'


    def commonInfos(self):
        docRepository = self.env['ir.attachment']._get_filestore()
        to_zone = tz.gettz(self.env.context.get('tz', 'Europe/Rome'))
        from_zone = tz.tzutc()
        dt = datetime.now()
        dt = dt.replace(tzinfo=from_zone)
        localDT = dt.astimezone(to_zone)
        localDT = localDT.replace(microsecond=0)
        msg = "Printed by '%(print_user)s' : %(date_now)s State: %(state)s"
        msg_vals = {
            'print_user': 'user_id.name',
            'date_now': localDT.ctime(),
            'state': 'doc_obj.engineering_state',
                }
        mainBookCollector = BookCollector(jumpFirst=False,
                                          customText=(msg, msg_vals),
                                          bottomHeight=10,
                                          poolObj=self.env)
        return docRepository, mainBookCollector

    def getDocument(self, 
                    product, 
                    check):
        out = []
        for doc in product.linkeddocuments:
            if check:
                if not doc.engineering_state in ['released', 
                                                 'undermodify']:
                    continue
            out.append((product,
                        doc))
        return out

    @api.model
    def _render_qweb_pdf(self, 
                         products=None, 
                         level=0, 
                         checkState=False):
        docRepository, mainBookCollector = self.commonInfos()
        documents = []

        for product in products:
            documents.extend(self.getDocument(product, checkState))
            if level > -1:
                for childProduct in product._getChildrenBom(product, level):
                    childProduct = self.env['product.product'].browse(childProduct)
                    documents.extend(self.getDocument(childProduct, checkState))
        if len(documents) == 0:
            content = getEmptyDocument()
        else:
            documentContent = packDocumentsNew(docRepository,
                                               documents,
                                               mainBookCollector)
            content = documentContent[0]
        return content

    def render_qweb_pdf(self, 
                        products=None, 
                        level=0, 
                        checkState=False):
        content = self._render_qweb_pdf(products, level, checkState)
        byteString = b"data:application/pdf;base64," + base64.b64encode(content)
        return byteString.decode('UTF-8')

    @api.model
    def _get_report_values(self, 
                           docids, 
                           data=None):
        products = self.env['product.product'].browse(docids)
        return {'docs': products,
                'get_content': self.render_qweb_pdf}


class ReportOneLevelProductPdf(ReportProductPdf):
    _name = 'report.plm.one_product_pdf'
    _description = 'Report pdf'


class ReportAllLevelProductPdf(ReportProductPdf):
    _name = 'report.plm.all_product_pdf'
    _description = 'Report pdf'


class ReportProductionProductPdf(ReportProductPdf):
    _name = 'report.plm.product_production_pdf_latest'
    _description = 'Report pdf'


class ReportProductionOneProductPdf(ReportProductPdf):
    _name = 'report.plm.product_production_one_pdf_latest'
    _description = 'Report pdf'


class ReportProductionAllProductPdf(ReportProductPdf):
    _name = 'report.plm.product_production_all_pdf_latest'
    _description = 'Report pdf'
