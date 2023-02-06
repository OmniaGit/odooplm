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
import xmlrpc
import pytz
from odoo.exceptions import UserError

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_TIME_FORMAT)


def correctDate(fromTimeStr, context):
    utcDate = fromTimeStr.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(context.get('tz', 'Europe/Rome')))
    return utcDate.replace(tzinfo=None)


class Plm_box_document(models.Model):
    _inherit = 'ir.attachment'

    name = fields.Char(_('Attachment Name'), required=False)
    is_plm_box = fields.Boolean('Is Plm Box document')

    @api.model
    def create(self, vals):
        if self.env.context.get('default_is_plm_box', False):
            vals['is_plm_box'] = True
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
    def getNewSequencedName(self):
        return self.env.get('ir.sequence').get('ir.attachment')

    @api.model
    def getFilesFromName(self, vals):
        docName, docRevision = vals
        docIds = self.search([('name', '=', docName), ('revisionid', '=', docRevision)]).ids
        if docIds:
            return self.GetSomeFiles((docIds, [[], []], False))

    @api.model
    def checkInOrFalse(self, docDict):
        docName = docDict.get('name', '')
        docRev = docDict.get('revisionId', '')
        docContent = docDict.get('fileContent', '')
        force = docDict.get('force', False)
        lastupdate = docDict.get('lastupdate', '')
        docBrowseList = self.search([('name', '=', docName)])
        if not force:
            for document in docBrowseList:
                if lastupdate:
                    plm_cad_open = self.sudo().env['plm.cad.open'].getLastCadOpenByUser(document, self.env.user)
                    if lastupdate > plm_cad_open.create_date:
                        return 'File changed'
                else:
                    if isinstance(docContent, xmlrpc.client.Binary):
                        docContent = docContent.data
                    if isinstance(docContent, str):
                        docContent = docContent.encode(encoding='utf_8', errors='strict')
                    if document.datas != docContent:
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
        docBrwsList = self.search([('name', '=', docName), ('revisionid', '=', docRev)])
        for docBrws in docBrwsList:
            if docBrws.checkNewer():
                return False
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
    def saveBoxDocRel(self, box_id, doc_id):
        if not box_id:
            raise Exception('Cannot link an empty box')
        if not doc_id:
            raise Exception('Cannot link an empty document')
        boxBrws = self.env['plm.box'].browse(box_id)
        boxBrws.write({'document_rel': [(4, doc_id)]})
        return True

    @api.model
    def returnDocsOfFilesChanged(self, valuesDict):
        raise UserError('Not implemented')
        outDocs = []
        cad_open = self.env['plm.cad.open'].sudo()
        for doc_name, doc_rev, checksum in valuesDict.items():
            documents = self.search([('engineering_document_name', '=', doc_name),
                                     ('revisionid', '=', doc_rev)
                                     ])
            if not documents:
                cad_open_ids = cad_open.search([
                    ('checksum', '=', checksum)
                    ])
                outDocs.append(doc_name, doc_rev, checksum, 'toServer')
            for document in documents:
                flag, _user = document.checkoutByMeWithUser()
                if flag:
                    if document.checksum != checksum:
                        outDocs.append(doc_name, doc_rev, checksum, 'fromServer')
        return outDocs

    @api.model
    def getLastTime(self, oid, default=None):
        document = self.browse(oid)
        plm_cad_open = self.sudo().env['plm.cad.open'].getLastCadOpenByUser(document, self.env.user)
        return plm_cad_open.create_date or document.write_date or document.create_date

    @api.multi
    def getDocumentState(self):
        for docBrws in self:
            checkedOutByMe = docBrws._is_checkedout_for_me()
            checkedIn = docBrws.ischecked_in()
            if checkedOutByMe:
                return 'check-out-by-me'
            if not checkedIn:
                return 'check-out'
            else:
                return 'check-in'
        return 'check-out-by-me'

    @api.multi
    def getDocumentStateMulty(self):
        ret = {}
        for doc in self:
            ret[str(doc.id)] = doc.getDocumentState()
        return ret

    @api.model
    def checkDocumentPresent(self, doc_dict={}):
        for str_box_id, vals in doc_dict.items():
            box_id = int(str_box_id)
            box_brws = self.env['plm.box'].browse(box_id)
            evaluated = []
            for str_doc_id, doc_vals in vals.items():
                doc_id = int(str_doc_id)
                doc_brws = self.browse(doc_id)
                checksum = doc_vals.get('checksum', '')
                doc_dict[str_box_id][str_doc_id]['check_mode'] = doc_brws.getDocumentState()
                if doc_id in box_brws.document_rel.ids:
                    if not checksum:
                        doc_dict[str_box_id][str_doc_id]['update'] = 'download'
                    elif doc_brws.checksum != checksum:
                        doc_condition = doc_brws.getDocumentState()
                        if doc_condition == 'check-out-by-me':
                            doc_dict[str_box_id][str_doc_id]['update'] = 'upload'
                        else:
                            doc_dict[str_box_id][str_doc_id]['update'] = 'download'
                    else:
                        doc_dict[str_box_id][str_doc_id]['update'] = 'none'
                else:
                    cad_opens = self.env['plm.cad.open'].search([
                        ('document_id', '=', doc_id)
                        ])
                    if len(cad_opens.ids) > 1:
                        doc_dict[str_box_id][str_doc_id]['update'] = 'delete'
                    elif doc_brws:
                        doc_dict[str_box_id][str_doc_id]['update'] = 'delete'
                    else:
                        doc_dict[str_box_id][str_doc_id]['update'] = 'upload'
        logging.info('Box sincronize res %r' % (doc_dict))
        return doc_dict
                

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
