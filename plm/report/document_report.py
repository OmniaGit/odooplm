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
from .book_collector import packDocuments
from datetime import datetime
from dateutil import tz
import base64
from odoo import api
from odoo import models


class ReportDocumentPdf(models.AbstractModel):
    _name = 'report.plm.ir_attachment_pdf'
    _description = 'Report Document PDF'

    @api.model
    def _render_qweb_pdf(self, documents=None, data=None):
        docType = self.env['ir.attachment']
        docRepository = docType._get_filestore()
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
            'state': 'doc_obj.state',
                }
        output = BookCollector(jumpFirst=False, customText=(msg, msg_vals), bottomHeight=10, poolObj=self.env)
        return packDocuments(docRepository, documents, output)
        
    @api.model
    def render_qweb_pdf(self, documents=None, data=None):
        documentContent = self._render_qweb_pdf(documents, data)
        byteString = b"data:application/pdf;base64," + base64.b64encode(documentContent[0])
        return byteString.decode('UTF-8')

    @api.model
    def _get_report_values(self, docids, data=None):
        documents = self.env['ir.attachment'].browse(docids)
        return {'docs': documents,
                'get_content': self.render_qweb_pdf}
