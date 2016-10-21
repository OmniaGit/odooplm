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

from book_collector import BookCollector
from book_collector import packDocuments
from datetime import datetime
from dateutil import tz

from odoo.report.interface import report_int
import odoo


class document_custom_report(report_int):
    def create(self, cr, uid, ids, datas, context=None):
        env = odoo.api.Environment(cr, uid, context or {})
        docType = env['plm.document']
        docRepository = docType._get_filestore()
        documents = docType.browse(ids)
        userType = env['res.users']
        user = userType.browse(uid)
        to_zone = tz.gettz(context.get('tz', 'Europe/Rome'))
        from_zone = tz.tzutc()
        dt = datetime.now()
        dt = dt.replace(tzinfo=from_zone)
        localDT = dt.astimezone(to_zone)
        localDT = localDT.replace(microsecond=0)
        msg = "Printed by " + str(user.name) + " : " + str(localDT.ctime())
        output = BookCollector(jumpFirst=False, customTest=(False, msg), bottomHeight=10)
        return packDocuments(docRepository, documents, output)

document_custom_report('report.plm.document.pdf')
