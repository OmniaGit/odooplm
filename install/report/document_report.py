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
from report.interface   import report_int
from book_collector     import BookCollector,packDocuments
import time
import pooler

class document_custom_report(report_int):
    def create(self, cr, uid, ids, datas, context=None):
        self.pool = pooler.get_pool(cr.dbname)
        documents = self.pool.get('ir.attachment').browse(cr, uid, ids, context=context)
        userType=self.pool.get('res.users')
        user=userType.browse(cr, uid, uid, context=context)
        msg = "Printed by "+str(user.name)+" : "+ str(time.strftime("%d/%m/%Y %H:%M:%S"))
        output  = BookCollector(jumpFirst=False,customTest=(False,msg),bottomHeight=10)
        return packDocuments(documents,output)
    
document_custom_report('report.ir.attachment.pdf')