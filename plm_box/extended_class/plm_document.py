'''
Created on Mar 8, 2017

@author: daniel
'''
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2017 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
from odoo import models
from odoo import fields
from odoo import _
from odoo import api
import logging
import datetime
from dateutil import parser
import pytz

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_TIME_FORMAT)


def correctDate(fromTimeStr, context):
    serverUtcTime = parser.parse(fromTimeStr.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
    utcDate = serverUtcTime.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(context.get('tz', 'Europe/Rome')))
    return utcDate.replace(tzinfo=None)


class Plm_box_document(models.Model):
    _inherit = 'plm.document'

    name = fields.Char(_('Attachment Name'), required=False, readonly=True)

    @api.model
    def create(self, vals):
        if not vals.get('name', False):
            name = self.getNewSequencedName()
            vals['name'] = name
        return super(Plm_box_document, self).create(vals)

    @api.multi
    def getCheckOutUser(self):
        for docBrws in self:
            checkOutObj = self.env.get('plm.checkout')
            checkOutBrwsList = checkOutObj.search([('documentid', '=', docBrws.id)])
            for checkOutBrws in checkOutBrwsList:
                if checkOutBrws:
                    return self.getUserNameFromId(checkOutBrws.write_uid)
        return ''

    @api.model
    def getUserNameFromId(self, userId):
        userBrws = self.env.get('res.users').browse(userId)
        if not userBrws:
            logging.warning("[getUserNameFromId] Couldn able to find user name with id %r" % (userId))
            return ''
        return userBrws.name

    @api.model
    def getNewSequencedName(self, vals):
        return self.env.get('ir.sequence').get('plm.document')

    @api.model
    def getFilesFromName(self, vals):
        docName, docRevision = vals
        docIds = self.search([('name', '=', docName), ('revisionid', '=', docRevision)]).ids
        if docIds:
            files = self.GetSomeFiles((docIds, [[], []], False))
            if files:
                files[0] = list(files[0])
                files[0][0] = docName
                return files

    @api.model
    def checkInOrFalse(self, docDict):
        docName = docDict.get('name', '')
        docRev = docDict.get('revisionId', '')
        docContent = docDict.get('fileContent', '')
        force = docDict.get('force', False)
        docBrowseList = self.search([('name', '=', docName)])
        if docBrowseList and not force:
            if docBrowseList[0].datas != docContent:
                return 'File changed'
        docIds = self.search([('name', '=', docName), ('revisionid', '=', docRev)]).ids
        if len(docIds) == 1:
            chckOutDocs = self.env.get('plm.checkout').search([('documentid', '=', docIds[0]), ('userid', '=', self.env.uid)])
            chckOutDocs.unlink()
            return True
        return False

    @api.model
    def checkOutOrFalse(self, docDict):
        docName = docDict.get('name', '')
        docRev = docDict.get('revisionId', '')
        plmCheckOutObj = self.env.get('plm.checkout')
        docBrwsList = self.search([('name', '=', docName), ('revisionid', '=', docRev)]).ids
        for docBrws in docBrwsList:
            docState = docBrws.state
            docId = docBrws.id
            if not docState or docState != 'draft':
                return False
            if plmCheckOutObj.search([('documentid', '=', docId), ('userid', '=', self.env.uid)]):
                return True
            res = plmCheckOutObj.create({'documentid': docId, 'userid': self.env.uid})
            if res:
                return True
        return False

    @api.model
    def saveBoxDocRel(self, docDict):
        docName = docDict.get('docName', '')
        boxName = docDict.get('boxName', '')
        boxObj = self.env.get('plm.box')
        boxBrwsList = boxObj.search([('name', '=', boxName)])
        for boxBrws in boxBrwsList:
            docId = self.search([('name', '=', docName)]).ids
            if docId:
                res = boxBrws.write({'document_rel': [(4, docId[0])]})
                return res
        return False

    @api.model
    def updateDocValues(self, valuesDict):
        docBrwsList = self.search([('name', '=', valuesDict.get('docName', ''))])
        for docBrws in docBrwsList:
            del valuesDict['docName']
            if docBrws.write(valuesDict):
                writeVal = datetime.datetime.strptime(docBrws.write_date, DEFAULT_SERVER_DATETIME_FORMAT)
                return correctDate(writeVal, self.env.context)
        return False

    @api.model
    def returnDocsOfFilesChanged(self, valuesDict):
        outDocs = []
        for docName, (docContent, _writeDateClient) in valuesDict.items():
            if self.getDocumentState({'docName': docName}) == 'check-out-by-me':
                docBrowseList = self.search([('name', '=', docName)])
                for docBrowse in docBrowseList:
                    if docBrowse.datas != docContent:
                        outDocs.append(docName)
        return outDocs

    @api.model
    def getDocumentState(self, vals):
        docName = vals.get('docName', '')
        docBrwsList = self.search([('name', '=', docName)])
        for docBrws in docBrwsList:
            checkedOutByMe = docBrws._is_checkedout_for_me()
            checkedIn = docBrws.ischecked_in()
            if checkedOutByMe:
                return 'check-out-by-me'
            if not checkedIn:
                return 'check-out'
            else:
                return 'check-in'
        return 'check-out-by-me'

Plm_box_document()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
