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

from .book_collector import BookCollector
from .book_collector import packDocuments
from datetime import datetime
from dateutil import tz
from odoo import api
from odoo import models


class ReportBomStructureAll(models.AbstractModel):
    _name = 'report.plm.document_pdf'

    @api.model
    def render_qweb_pdf(self, documents=None, data=None):
        docType = self.env['plm.document']
        docRepository = docType._get_filestore()
        userType = self.env['res.users']
        user = userType.browse(self.env.uid)
        to_zone = tz.gettz(self.env.context.get('tz', 'Europe/Rome'))
        from_zone = tz.tzutc()
        dt = datetime.now()
        dt = dt.replace(tzinfo=from_zone)
        localDT = dt.astimezone(to_zone)
        localDT = localDT.replace(microsecond=0)
        msg = "Printed by " + str(user.name) + " : " + str(localDT.ctime())
        output = BookCollector(jumpFirst=False, customTest=(False, msg), bottomHeight=10)
        return packDocuments(docRepository, documents, output)

    @api.model
    def get_report_values(self, docids, data=None):
        documents = self.env['plm.document'].browse(docids)
        return self.render_qweb_pdf(documents, data)
