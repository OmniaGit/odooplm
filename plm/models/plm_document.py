# -*- encoding: utf-8 -*-
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
import random
import string
import base64
import os
import time
import json
from datetime import datetime
import odoo.tools as tools
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
from __builtin__ import False
_logger = logging.getLogger(__name__)


# To be adequated to plm.component class states
USED_STATES = [('draft', _('Draft')),
               ('confirmed', _('Confirmed')),
               ('released', _('Released')),
               ('undermodify', _('UnderModify')),
               ('obsoleted', _('Obsoleted'))]
USEDIC_STATES = dict(USED_STATES)


def random_name():
    random.seed()
    d = [random.choice(string.ascii_letters) for _x in xrange(20)]
    return ("".join(d))


def create_directory(path):
    dir_name = random_name()
    path = os.path.join(path, dir_name)
    os.makedirs(path)
    return dir_name


class PlmDocument(models.Model):
    _name = 'plm.document'
    _table = 'plm_document'
    _inherit = ['mail.thread', 'ir.attachment']

    @api.multi
    def get_checkout_user(self):
        lastDoc = self._getlastrev(self.ids)
        if lastDoc:
            for docBrws in self.env['plm.checkout'].search([('documentid', '=', lastDoc[0])]):
                return docBrws.userid
        return False

    @api.multi
    def _is_checkedout_for_me(self):
        """
            Get if given document (or its latest revision) is checked-out for the requesting user
        """
        userBrws = self.get_checkout_user()
        if userBrws:
            if userBrws.id == self.env.uid:
                return True
        return False

    @api.multi
    def _getlastrev(self, resIds):
        result = []
        for objDoc in self.browse(resIds):
            docIds = self.search([('name', '=', objDoc.name)], order='revisionid').ids
            docIds.sort()   # Ids are not surely ordered, but revision are always in creation order.
            if docIds:
                result.append(docIds[len(docIds) - 1])
            else:
                logging.warning('[_getlastrev] No documents are found for object with name: "%s"' % (objDoc.name))
        return list(set(result))

    @api.multi
    def GetLastNamesFromID(self):
        """
            get the last rev
        """
        newIds = self._getlastrev(self.ids)
        return self.browse(newIds).read(['datas_fname'])

    @api.multi
    def _data_get_files(self, listedFiles=([], []), forceFlag=False):
        """
            Get Files to return to Client
        """
        result = []
        datefiles, listfiles = listedFiles
        for objDoc in self:
            if objDoc.type == 'binary':
                timeDoc = self.getLastTime(objDoc.id)
                timeSaved = time.mktime(timeDoc.timetuple())
                try:
                    isCheckedOutToMe = objDoc._is_checkedout_for_me()
                    if not(objDoc.datas_fname in listfiles):
                        if (not objDoc.store_fname) and (objDoc.db_datas):
                            value = objDoc.db_datas
                        else:
                            value = file(os.path.join(self._get_filestore(), objDoc.store_fname), 'rb').read()
                        result.append((objDoc.id, objDoc.datas_fname, base64.encodestring(value), isCheckedOutToMe, timeDoc))
                    else:
                        if forceFlag:
                            isNewer = True
                        else:
                            timefile = time.mktime(datetime.strptime(str(datefiles[listfiles.index(objDoc.datas_fname)]), '%Y-%m-%d %H:%M:%S').timetuple())
                            isNewer = (timeSaved - timefile) > 5
                        if (isNewer and not(isCheckedOutToMe)):
                            if (not objDoc.store_fname) and (objDoc.db_datas):
                                value = objDoc.db_datas
                            else:
                                value = file(os.path.join(self._get_filestore(), objDoc.store_fname), 'rb').read()
                            result.append((objDoc.id, objDoc.datas_fname, base64.encodestring(value), isCheckedOutToMe, timeDoc))
                        else:
                            result.append((objDoc.id, objDoc.datas_fname, False, isCheckedOutToMe, timeDoc))
                except Exception, ex:
                    logging.error("_data_get_files : Unable to access to document (" + str(objDoc.name) + "). Error :" + str(ex))
                    result.append((objDoc.id, objDoc.datas_fname, False, True, self.getServerTime()))
        return result

    @api.depends('store_fname', 'db_datas')
    def _compute_datas(self):
        for objDoc in self:
            if objDoc.type == 'binary':
                if objDoc.store_fname:
                    filestore = os.path.join(self._get_filestore(), objDoc.store_fname)
                    if os.path.exists(filestore):
                        objDoc.datas = file(filestore, 'rb').read().encode('base64')
                else:
                    objDoc.datas = objDoc.db_datas

    @api.multi
    def _inverse_datas(self):
        filestore = self._get_filestore()
        for docBrws in self:
            oid = docBrws.id
            if docBrws.type == 'binary':
                value = docBrws.datas
                if not value:
                    filename = docBrws.store_fname
                    try:
                        os.unlink(os.path.join(filestore, filename))
                    except:
                        pass
                    self.env.cr.execute('update plm_document set store_fname=NULL WHERE id=%s', (oid,))
                    return True
                printout = False
                preview = False
                if docBrws.printout:
                    printout = docBrws.printout
                if docBrws.preview:
                    preview = docBrws.preview
                db_datas = b''                    # Clean storage field.
                fname, filesize = self._manageFile(filestore, value)
                self.env.cr.execute('update plm_document set store_fname=%s,file_size=%s,db_datas=%s where id=%s', (fname,
                                                                                                                    filesize,
                                                                                                                    db_datas,
                                                                                                                    oid))
                self.env['plm.backupdoc'].create({'userid': self.env.uid,
                                                  'existingfile': fname,
                                                  'documentid': oid,
                                                  'printout': printout,
                                                  'preview': preview
                                                  })

    @api.model
    def _explodedocs(self, oid, kinds, listed_documents=[], recursion=True):
        result = []
        documentRelation = self.env['plm.document.relation']

        def getAllDocumentChildId(fromID, kinds):
            docRelBrwsList = documentRelation.search([('parent_id', '=', fromID), ('link_kind', 'in', kinds)])
            for child in docRelBrwsList:
                idToAdd = child.child_id.id
                if idToAdd not in result:
                    result.append(idToAdd)
                    if recursion:
                        getAllDocumentChildId(idToAdd, kinds)
        getAllDocumentChildId(oid, kinds)
        return result

    @api.model
    def _relateddocs(self, oid, kinds, listed_documents=[], recursion=True):
        result = []
        if (oid in listed_documents):
            return result
        documentRelation = self.env['plm.document.relation']
        docBrwsList = documentRelation.search([('child_id', '=', oid), ('link_kind', 'in', kinds)])
        if len(docBrwsList) == 0:
            return []
        for child in docBrwsList:
            if recursion:
                listed_documents.append(oid)
                result.extend(self._relateddocs(child.parent_id.id, kinds, listed_documents, recursion))
            if child.parent_id:
                result.append(child.parent_id.id)
        return list(set(result))

    @api.model
    def _relatedbydocs(self, oid, kinds, listed_documents=[], recursion=True):
        result = []
        if (oid in listed_documents):
            return result
        documentRelation = self.env['plm.document.relation']
        docBrwsList = documentRelation.search([('parent_id', '=', oid), ('link_kind', 'in', kinds)])
        if len(docBrwsList) == 0:
            return []
        for child in docBrwsList:
            if recursion:
                listed_documents.append(oid)
                result.extend(self._relatedbydocs(child.child_id.id, kinds, listed_documents, recursion))
            if child.child_id.id:
                result.append(child.child_id.id)
        return list(set(result))

    @api.multi
    def _data_check_files(self, targetIds, listedFiles=(), forceFlag=False):
        result = []
        datefiles = []
        listfiles = []
        if len(listedFiles) > 0:
            datefiles, listfiles = listedFiles
        for objDoc in self.browse(targetIds):
            if objDoc.type == 'binary':
                checkOutUser = ''
                isCheckedOutToMe = False
                timeDoc = self.getLastTime(objDoc.id)
                timeSaved = time.mktime(timeDoc.timetuple())
                checkoutUserBrws = objDoc.get_checkout_user()
                if checkoutUserBrws:
                    checkOutUser = checkoutUserBrws.name
                    if checkoutUserBrws.id == self.env.uid:
                        isCheckedOutToMe = True
                if (objDoc.datas_fname in listfiles):
                    if forceFlag:
                        isNewer = True
                    else:
                        listFileIndex = listfiles.index(objDoc.datas_fname)
                        timefile = time.mktime(datetime.strptime(str(datefiles[listFileIndex]), '%Y-%m-%d %H:%M:%S').timetuple())
                        isNewer = (timeSaved - timefile) > 5
                    collectable = isNewer and not(isCheckedOutToMe)
                else:
                    collectable = True
                objDatas = False
                try:
                    objDatas = objDoc.datas
                except Exception, ex:
                    logging.error('Document with "id": %s  and "name": %s may contains no data!!         Exception: %s' % (objDoc.id, objDoc.name, ex))
                if (objDoc.file_size < 1) and (objDatas):
                    file_size = len(objDoc.datas)
                else:
                    file_size = objDoc.file_size
                result.append((objDoc.id, objDoc.datas_fname, file_size, collectable, isCheckedOutToMe, checkOutUser))
        return list(set(result))

    @api.multi
    def copy(self, defaults={}):
        """
            Overwrite the default copy method
        """
        documentRelation = self.env['plm.document.relation']
        docBrwsList = documentRelation.search([('parent_id', '=', self.id)])
        previous_name = self.name
        if 'name' not in defaults:
            new_name = 'Copy of %s' % previous_name
            l = self.search([('name', '=', new_name)], order='revisionid')
            if len(l) > 0:
                new_name = '%s (%s)' % (new_name, len(l) + 1)
            defaults['name'] = new_name
        fname, filesize = self._manageFile()
        defaults['store_fname'] = fname
        defaults['file_size'] = filesize
        defaults['state'] = 'draft'
        defaults['writable'] = True
        newDocBrws = super(PlmDocument, self).copy(defaults)
        if newDocBrws:
            newDocBrws.wf_message_post(body=_('Copied starting from : %s.' % previous_name))
        for brwEnt in docBrwsList:
            documentRelation.create({
                                    'parent_id': newDocBrws.id,
                                    'child_id': brwEnt.child_id.id,
                                    'configuration': brwEnt.configuration,
                                    'link_kind': brwEnt.link_kind,
                                    })
        return newDocBrws.id

    @api.multi
    def _manageFile(self, filestore=False, binvalue=None):
        """
            use given 'binvalue' to save it on physical repository and to read size (in bytes).
        """
        if not filestore:
            filestore = self._get_filestore()
            if not filestore:
                raise UserError(_('Filestore not set!'))
        flag = None
        # This can be improved
        for dirs in os.listdir(filestore):
            if os.path.isdir(os.path.join(filestore, dirs)) and len(os.listdir(os.path.join(filestore, dirs))) < 4000:
                flag = dirs
                break
        if binvalue is None:
            fileStream = self._data_get(name=None, arg=None)
            binvalue = fileStream[fileStream.keys()[0]]

        flag = flag or create_directory(filestore)
        filename = random_name()
        fname = os.path.join(filestore, flag, filename)
        fobj = file(fname, 'wb')
        value = base64.decodestring(binvalue)
        fobj.write(value)
        fobj.close()
        return (os.path.join(flag, filename), len(value))

    @api.multi
    def _data_get(self, name, arg):
        result = {}
        for objDoc in self:
            if objDoc.type == 'binary':
                value = ''
                if not objDoc.store_fname:
                    value = objDoc.db_datas
                else:
                    filestore = os.path.join(self._get_filestore(), objDoc.store_fname)
                    if os.path.exists(filestore):
                        value = file(filestore, 'rb').read()
                    else:
                        msg = "Document %s-%s is not in %r" % (str(objDoc.name),
                                                               str(objDoc.revisionid),
                                                               filestore)

                        logging.error(msg)
                if value and len(value) > 0:
                    result[objDoc.id] = base64.encodestring(value)
                else:
                    result[objDoc.id] = ''
                    msg = "Document %s - %s cannot be accessed" % (str(objDoc.name),
                                                                   str(objDoc.revisionid))
                    logging.warning(msg)
        return result

    @api.model
    def _iswritable(self, oid):
        if not oid.type == 'binary':
            logging.warning("_iswritable : Part (" + str(oid.name) + "-" + str(oid.revisionid) + ") not writable as hyperlink.")
            return False
        if oid.state not in ('draft'):
            logging.warning("_iswritable : Part (" + str(oid.name) + "-" + str(oid.revisionid) + ") in status ; " + str(oid.state) + ".")
            return False
        if not oid.name:
            logging.warning("_iswritable : Part (" + str(oid.name) + "-" + str(oid.revisionid) + ") without Engineering P/N.")
            return False
        return True

    @api.multi
    def newVersion(self):
        """
            create a new version of the document (to WorkFlow calling)
        """
        if self.NewRevision() is not None:
            return True
        return False

    @api.multi
    def NewRevision(self):
        """
            create a new revision of the document
        """
        newID = None
        newRevIndex = False
        for tmpObject in self:
            latestIDs = self.GetLatestIds([(tmpObject.name, tmpObject.revisionid, False)])
            for oldObject in self.browse(latestIDs):
                oldObject.with_context({'check': False}).write({'state': 'undermodify'})
                defaults = {}
                newRevIndex = int(oldObject.revisionid) + 1
                defaults['name'] = oldObject.name
                defaults['revisionid'] = newRevIndex
                defaults['writable'] = True
                defaults['state'] = 'draft'
                res = super(PlmDocument, oldObject).copy(defaults)
                newID = res.id
                oldObject.wf_message_post(body=_('Created : New Revision.'))
                break
            break
        return (newID, newRevIndex)

    @api.multi
    def Clone(self, defaults={}):
        """
            create a new copy of the document
        """
        exitValues = {}
        newID = self.copy(defaults)
        if newID is not None:
            newEnt = self.browse(newID)
            exitValues['_id'] = newID
            exitValues['name'] = newEnt.name
            exitValues['revisionid'] = newEnt.revisionid
        return exitValues

    @api.model
    def CheckSaveUpdate(self, documents, default=None):
        """
            Save or Update Documents
        """
        retValues = []
        for document in documents:
            hasToBeSaved = False
            if not ('name' in document) or ('revisionid' not in document):
                document['documentID'] = False
                document['hasSaved'] = hasToBeSaved
                continue
            docBrwsList = self.search([('name', '=', document['name']),
                                      ('revisionid', '=', document['revisionid'])],
                                      order='revisionid')
            existingID = False
            if not docBrwsList:
                hasToBeSaved = True
            else:
                for existingBrws in docBrwsList:
                    existingID = existingBrws.id
                    if existingBrws.writable:
                        if existingBrws.file_size > 0 and existingBrws.datas_fname:
                            if self.getLastTime(existingID) < datetime.strptime(str(document['lastupdate']), '%Y-%m-%d %H:%M:%S'):
                                hasToBeSaved = True
                        else:
                            hasToBeSaved = True
                    break
            document['documentID'] = existingID
            document['hasSaved'] = hasToBeSaved
            retValues.append(document)
        return retValues

    @api.model
    def SaveOrUpdate(self, documents, default=None):
        """
            Save or Update Documents
        """
        retValues = []
        for document in documents:
            hasSaved = False
            hasUpdated = False
            if not ('name' in document) or ('revisionid' not in document):
                document['documentID'] = False
                document['hasSaved'] = hasSaved
                document['hasUpdated'] = hasUpdated
                continue
            docBrwsList = self.search([('name', '=', document['name']), ('revisionid', '=', document['revisionid'])], order='revisionid')
            if not docBrwsList:
                existingID = self.create(document).id
                hasSaved = True
            else:
                existingID = docBrwsList[0].id
                if self.getLastTime(existingID) < datetime.strptime(str(document['lastupdate']), '%Y-%m-%d %H:%M:%S'):
                    if self._iswritable(docBrwsList[0]):
                        del(document['lastupdate'])
                        if not self.browse([existingID]).write(document, check=True):
                            raise UserError(_("Document %s  -  %s cannot be updated" % (str(document['name']), str(document['revisionid']))))
                        hasSaved = True
            document['documentID'] = existingID
            document['hasSaved'] = hasSaved
            document['hasUpdated'] = hasUpdated
            retValues.append(document)
        return retValues

    @api.model
    def RegMessage(self, request, default=None):
        """
            Registers a message for requested document
        """
        oid, message = request
        self.browse([oid]).wf_message_post(body=_(message))
        return False

    @api.model
    def UpdateDocuments(self, documents, default=None):
        """
            Save or Update Documents
        """
        ret = True
        for document in documents:
            oid = document['documentID']
            del(document['documentID'])
            ret = ret and self.browse([oid]).write(document, check=True)
        return ret

    @api.multi
    def CleanUp(self, default=None):
        """
            Remove faked documents
        """
        self.env.cr.execute("delete from plm_document where store_fname=NULL and type='binary'")
        return True

    @api.model
    def QueryLast(self, request=([], []), default=None):
        """
            Query to return values based on columns selected.
        """
        expData = []
        queryFilter, columns = request
        if len(columns) < 1:
            return expData
        if 'revisionid' in queryFilter:
            del queryFilter['revisionid']
        docBrwsList = self.search(queryFilter, order='revisionid')
        if len(docBrwsList) > 0:
            tmpData = docBrwsList.export_data(columns)
            if 'datas' in tmpData:
                expData = tmpData['datas']
        return expData

    @api.multi
    def ischecked_in(self):
        """
            Check if a document is checked-in
        """
        checkoutType = self.env['plm.checkout']
        for document in self:
            if checkoutType.search([('documentid', '=', document.id)]):
                logging.warning(_("The document %s - %s has not checked-in" % (str(document.name), str(document.revisionid))))
                return False
        return True

    @api.multi
    def wf_message_post(self, body=''):
        """
            Writing messages to follower, on multiple objects
        """
        if body:
            for elem in self:
                elem.message_post(body=_(body))

    @api.multi
    def setCheckContextWrite(self, checkVal=True):
        '''
            :checkVal Set check flag in context to do state verification in component write
        '''
        localCtx = self.env.context.copy()
        localCtx['check'] = checkVal
        self.env.context = localCtx

    @api.multi
    def commonWFAction(self, writable, state, check):
        '''
            :writable set writable flag for component
            :state define new product state
            :check do state verification in component write
        '''
        self.setCheckContextWrite(check)
        objId = self.write({'writable': writable,
                            'state': state
                            })
        if objId:
            self.wf_message_post(body=_('Status moved to: %s.' % (USEDIC_STATES[state])))
        return objId

    @api.multi
    def action_draft(self):
        """
            action to be executed for Draft state
        """
        return self.commonWFAction(True, 'draft', False)

    @api.multi
    def action_confirm(self):
        """
            action to be executed for Confirm state
        """
        return self.commonWFAction(False, 'confirmed', False)

    @api.multi
    def action_release(self):
        """
            release the object
        """
        for oldObject in self:
            lastDocBrws = self._getbyrevision(oldObject.name, oldObject.revisionid - 1)
            if lastDocBrws:
                lastDocBrws.commonWFAction(False, 'released', False)
        if self.ischecked_in():
            return self.commonWFAction(False, 'released', False)
        return False

    @api.multi
    def action_obsolete(self):
        """
            obsolete the object
        """
        return self.commonWFAction(False, 'obsoleted', False)

    @api.multi
    def action_reactivate(self):
        """
            reactivate the object
        """
        defaults = {}
        defaults['engineering_writable'] = False
        defaults['state'] = 'draft'
        if self.ischecked_in():
            self.setCheckContextWrite(False)
            objId = self.write(defaults)
            if objId:
                self.wf_message_post(body=_('Status moved to:%s.' % (USEDIC_STATES[defaults['state']])))
            return objId
        return False

    @api.multi
    def blindwrite(self, vals):
        """
            blind write for xml-rpc call for recovering porpouse
            DO NOT USE FOR COMMON USE !!!!
        """
        return self.with_context({'check': False}).write(vals)

#   Overridden methods for this entity
    @api.model
    def _get_filestore(self):
        dms_Root_Path = tools.config.get('document_path', os.path.join(tools.config['root_path'], 'filestore'))
        filestore = os.path.join(dms_Root_Path, self.env.cr.dbname)
        try:
            os.makedirs(filestore)
        except OSError, ex:
            if ex.errno not in [13, 17]:
                raise ex
            if ex.errno == 13:
                logging.warning(_("Permission denied for folder %r." % (str(filestore))))
                return ''
        return filestore

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        return super(PlmDocument, self).search(args, offset, limit, order, count)

    @api.model
    def create(self, vals):
        return super(PlmDocument, self).create(vals)

    @api.multi
    def write(self, vals):
        checkState = ('confirmed', 'released', 'undermodify', 'obsoleted')
        check = self.env.context.get('check', True)
        if check:
            for customObject in self:
                if customObject.state in checkState:
                    raise UserError(_("The active state does not allow you to make save action"))
                    return False
        return super(PlmDocument, self).write(vals)

    @api.multi
    def unlink(self):
        values = {'state': 'released', }
        checkState = ('undermodify', 'obsoleted')
        for checkObj in self:
            docBrwsList = self.search([('name', '=', checkObj.name), ('revisionid', '=', checkObj.revisionid - 1)])
            if len(docBrwsList) > 0:
                oldObject = docBrwsList[0]
                if oldObject.state in checkState:
                    oldObject.wf_message_post(body=_('Removed : Latest Revision.'))
                    if not oldObject.with_context({'check': False}).write(values):
                        logging.warning("unlink : Unable to update state to old document (" + str(oldObject.name) + "-" + str(oldObject.revisionid) + ").")
                        return False
        return super(PlmDocument, self).unlink()

#   Overridden methods for this entity
    @api.model
    def _check_duplication(self, vals, ids=None, op='create'):
        SUPERUSER_ID = 1
        name = vals.get('name', False)
        parent_id = vals.get('parent_id', False)
        ressource_parent_type_id = vals.get('ressource_parent_type_id', False)
        ressource_id = vals.get('ressource_id', 0)
        revisionid = vals.get('revisionid', 0)
        if op == 'write':
            for directory in self.browse(ids):
                if not name:
                    name = directory.name
                if not parent_id:
                    parent_id = directory.parent_id and directory.parent_id.id or False
                # TODO fix algo
                if not ressource_parent_type_id:
                    ressource_parent_type_id = directory.ressource_parent_type_id and directory.ressource_parent_type_id.id or False
                if not ressource_id:
                    ressource_id = directory.ressource_id and directory.ressource_id or 0
                docBrwsList = self.search([('id', '<>', directory.id),
                                           ('name', '=', name),
                                           ('parent_id', '=', parent_id),
                                           ('ressource_parent_type_id', '=', ressource_parent_type_id),
                                           ('ressource_id', '=', ressource_id),
                                           ('revisionid', '=', revisionid)])
                if docBrwsList:
                    return False
        if op == 'create':
            docBrwsList = self.search(SUPERUSER_ID,
                                      [('name', '=', name),
                                       ('parent_id', '=', parent_id),
                                       ('ressource_parent_type_id', '=', ressource_parent_type_id),
                                       ('ressource_id', '=', ressource_id),
                                       ('revisionid', '=', revisionid)])
            if docBrwsList:
                return False
        return True
#   Overridden methods for this entity

    @api.one
    def _get_checkout_state(self):
        chechRes = self.getCheckedOut(self.id, None)
        if chechRes:
            self.checkout_user = str(chechRes[2])
        else:
            self.checkout_user = ''

    @api.model
    def CheckIn(self, attrs):
        documentName = attrs.get('name', '')
        revisionId = attrs.get('revisionid', False)
        docBrwsList = self.search([('name', '=', documentName),
                                   ('revisionid', '=', revisionId)])
        for docBrws in docBrwsList:
            checkOutId = docBrws.isCheckedOutByMe()
            if not checkOutId:
                logging.info('Document %r is not in check out by user %r so cannot be checked-in' % (docBrws.id, self.env.user_id))
                return False
            if docBrws.file_size <= 0 or not docBrws.datas_fname:
                logging.warning('Document %r has not document content so cannot be checked-in' % (docBrws.id))
                return False
            self.env['plm.checkout'].browse(checkOutId).unlink()
            return docBrws.id
        return False

    @api.one
    def _is_checkout(self):
        chechRes = self.getCheckedOut(self.id, None)
        if chechRes:
            self.is_checkout = True
        else:
            self.is_checkout = False

    def getFileExtension(self, docBrws):
        fileExtension = ''
        datas_fname = docBrws.datas_fname
        if datas_fname:
            fileExtension = '.' + datas_fname.split('.')[-1]
        return fileExtension

    @api.multi
    def _compute_document_type(self):
        configParamObj = self.env['ir.config_parameter']
        str2DExtensions = configParamObj._get_param('file_exte_type_rel_2D')
        str3DExtensions = configParamObj._get_param('file_exte_type_rel_3D')
        for docBrws in self:
            try:
                fileExtension = docBrws.getFileExtension(docBrws)
                extensions2D = eval(str2DExtensions)
                extensions3D = eval(str3DExtensions)
                if fileExtension in extensions2D:
                    docBrws.document_type = '2d'
                elif fileExtension in extensions3D:
                    docBrws.document_type = '3d'
                else:
                    docBrws.document_type = 'other'
            except Exception, ex:
                logging.error('Unable to compute document type for document %r, error %r' % (docBrws.id, ex))

    revisionid = fields.Integer(_('Revision Index'),
                                default=0,
                                required=True)
    writable = fields.Boolean(_('Writable'),
                              default=True)
    printout = fields.Binary(_('Printout Content'),
                             help=_("Print PDF content."))
    preview = fields.Binary(_('Preview Content'),
                            help=_("Static preview."))
    state = fields.Selection(USED_STATES,
                             _('Status'),
                             help=_("The status of the product."),
                             readonly="True",
                             default='draft',
                             required=True)
    checkout_user = fields.Char(string=_("Checked-Out to"),
                                compute=_get_checkout_state)
    is_checkout = fields.Boolean(_('Is Checked-Out'),
                                 compute=_is_checkout,
                                 store=False)
    linkedcomponents = fields.Many2many('product.product',
                                        'plm_component_document_rel',
                                        'document_id',
                                        'component_id',
                                        _('Linked Parts'))
    datas = fields.Binary(string='File Content', compute='_compute_datas', inverse='_inverse_datas')
    datas = fields.Binary(string=_('File Content'),
                          compute='_compute_datas',
                          inverse='_inverse_datas',
                          method=True)
    document_type = fields.Selection([('other', _('Other')),
                                      ('2d', _('2D')),
                                      ('3d', _('3D')),
                                      ], 
                                     compute=_compute_document_type,
                                     string= _('Document Type'))
    desc_modify = fields.Text(_('Modification Description'), default='')

    _sql_constraints = [
        ('name_unique', 'unique (name, revisionid)', 'File name has to be unique!')  # qui abbiamo la sicurezza dell'univocita del nome file
    ]

    @api.model
    def CheckedIn(self, files, default=None):
        """
            Get checked status for requested files
        """
        retValues = []

        def getcheckedfiles(files):
            res = []
            for fileName in files:
                plmDocList = self.search([('datas_fname', '=', fileName)], order='revisionid')
                if len(plmDocList) > 0:
                    ids = plmDocList.ids
                    ids.sort()
                    docBrws = self.browse(ids[len(ids) - 1])
                    checkoutFlag = docBrws._is_checkedout_for_me()
                    res.append([fileName, not checkoutFlag])
            return res
        if len(files) > 0:  # no files to process
            retValues = getcheckedfiles(files)
        return retValues

    @api.model
    def GetUpdated(self, vals):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        docData, attribNames = vals
        ids = self.GetLatestIds(docData)
        return self.read(list(set(ids)), attribNames)

    @api.model
    def GetLatestIds(self, vals, forceCADProperties=False):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        ids = []

        def getCompIds(docName, docRev):
            if docRev is None or docRev is False:
                docBrwsList = self.search([('name', '=', docName)], order='revisionid')
                if len(docBrwsList) > 0:
                    ids.append(docBrwsList.ids[-1])
            else:
                ids.extend(self.search([('name', '=', docName), ('revisionid', '=', docRev)]).ids)

        for docName, docRev, docIdToOpen in vals:
            docBrowse = self.browse(docIdToOpen)
            checkOutUser = docBrowse.get_checkout_user()
            if checkOutUser:
                isMyDocument = docBrowse.isCheckedOutByMe()
                if isMyDocument:
                    return []    # Document properties will be not updated
                else:
                    getCompIds(docName, docRev)
            else:
                getCompIds(docName, docRev)
        return list(set(ids))

    @api.multi
    def isCheckedOutByMe(self):
        checkoutBrwsList = self.env['plm.checkout'].search([('documentid', '=', self.id), ('userid', '=', self.env.uid)])
        for checkoutBrws in checkoutBrwsList:
            return checkoutBrws.id
        return None

    @api.model
    def CheckAllFiles(self, request, default=None):
        """
            Evaluate documents to return
        """
        forceFlag = False
        listed_models = []
        listed_documents = []
        outIds = []
        oid, listedFiles, selection = request
        outIds.append(oid)
        if selection is False:
            selection = 1   # Case of selected
        if selection < 0:   # Case of force refresh PWS
            forceFlag = True
            selection = selection * (-1)
        # Get relations due to layout connected
        docArray = self._relateddocs(oid, ['LyTree'], listed_documents)
        # Get Hierarchical tree relations due to children
        modArray = self._explodedocs(oid, ['HiTree'], listed_models)
        outIds = list(set(outIds + modArray + docArray))
        if selection == 2:  # Case of latest
            outIds = self._getlastrev(outIds)
        return self._data_check_files(outIds, listedFiles, forceFlag)

    @api.model
    def CheckInRecursive(self, request, default=None):
        """
            Evaluate documents to return
        """
        def getDocId(args):
            docName = args.get('name')
            docRev = args.get('revisionid')
            docBrwsList = self.search([('name', '=', docName), ('revisionid', '=', docRev)])
            if not docBrwsList:
                logging.warning('Document with name "%s" and revision "%s" not found' % (docName, docRev))
                return False
            return docBrwsList[0].id

        oid, _listedFiles, selection = request
        oid = getDocId(oid)
        docBrws = self.browse(oid)
        checkRes = self.browse(oid).isCheckedOutByMe()
        if not checkRes:
            logging.info('Document %r is not in check out by user %r so cannot be checked-in recursively' % (oid, self.env.uid))
            return False
        if docBrws.file_size <= 0 or not docBrws.datas_fname:
            logging.warning('Document %r has not document content so cannot be checked-in recirsively' % (oid))
            return False
        if selection is False:
            selection = 1
        if selection < 0:
            selection = selection * (-1)
        documentRelation = self.env['plm.document.relation']
        docArray = []

        def recursionCompute(oid):
            if oid in docArray:
                return
            else:
                docArray.append(oid)
            docBrwsList = documentRelation.search(['|', ('parent_id', '=', oid), ('child_id', '=', oid)])
            for objRel in docBrwsList:
                if objRel.link_kind in ['LyTree', 'RfTree'] and objRel.child_id.id not in docArray:
                    docArray.append(objRel.child_id.id)
                else:
                    if objRel.parent_id.id == oid:
                        recursionCompute(objRel.child_id.id)

        recursionCompute(oid)
        if selection == 2:
            docArray = self._getlastrev(docArray)
        checkoutObj = self.env['plm.checkout']
        for docId in docArray:
            checkOutBrwsList = checkoutObj.search([('documentid', '=', docId), ('userid', '=', self.env.uid)])
            checkOutBrwsList.unlink()
        return self.browse(docArray).read(['datas_fname'])

    @api.model
    def GetSomeFiles(self, request, default=None):
        """
            Extract documents to be returned
        """
        forceFlag = False
        ids, listedFiles, selection = request
        if not selection:
            selection = 1

        if selection < 0:
            forceFlag = True
            selection = selection * (-1)

        if selection == 2:
            docArray = self._getlastrev(ids)
        else:
            docArray = ids
        return self.browse(docArray)._data_get_files(listedFiles, forceFlag)

    @api.model
    def GetAllFiles(self, request, default=None):
        """
            Extract documents to be returned
        """
        forceFlag = False
        listed_models = []
        listed_documents = []
        modArray = []
        oid, listedFiles, selection = request
        if not selection:
            selection = 1

        if selection < 0:
            forceFlag = True
            selection = selection * -1

        kind = 'HiTree'                   # Get Hierarchical tree relations due to children
        docArray = self._explodedocs(oid, [kind], listed_models)
        if oid not in docArray:
            docArray.append(oid)        # Add requested document to package
        for item in docArray:
            kinds = ['LyTree', 'RfTree']               # Get relations due to layout connected
            modArray.extend(self._relateddocs(item, kinds, listed_documents))
            modArray.extend(self._explodedocs(item, kinds, listed_documents))
        modArray.extend(docArray)
        docArray = list(set(modArray))    # Get unique documents object IDs
        if selection == 2:
            docArray = self._getlastrev(docArray)
        if oid not in docArray:
            docArray.append(oid)     # Add requested document to package
        return self.browse(docArray)._data_get_files(listedFiles, forceFlag)

    @api.multi
    def GetRelatedDocs(self, default=None):
        """
            Extract documents related to current one(s) (layouts, referred models, etc.)
        """
        related_documents = []
        listed_documents = []
        read_docs = []
        for oid in self.ids:
            kinds = ['RfTree',
                     'LyTree',
                     '']   # Fix for new style document relations
            read_docs.extend(self._relateddocs(oid, kinds, listed_documents, False))
            read_docs.extend(self._relatedbydocs(oid, kinds, listed_documents, False))
        for document in self.browse(read_docs):
            related_documents.append([document.id, document.name, document.preview])
        return related_documents

    @api.model
    def GetRelatedDocsByAttrs(self, docPropsList=[]):
        """
            Extract documents related to current one(s) (layouts, referred models, etc.)
        """
        if not docPropsList:
            return False
        docProps = docPropsList[0]
        docRev = docProps.get('revisionid', None)
        if docRev is None:
            logging.warning('Current document has not revisionid attribute %r.\n Cannot get related documents.' % (docProps))
            return False
        docName = docProps.get('name', '')
        documentBrws = self.search([('name', '=', docName), ('revisionid', '=', docRev)])
        if not documentBrws:
            logging.warning('Unbale to find document %r with revision %r.\n Cannot get related documents.' % (docName, docRev))
            return False
        return documentBrws.GetRelatedDocs()

    @api.model
    def getServerTime(self, _unusedVal=False):
        """
            calculate the server db time
        """
        return datetime.now()

    @api.model
    def getLastTime(self, oid, default=None):
        """
            get document last modification time
        """
        obj = self.browse(oid)
        if(obj.write_date is not False):
            return datetime.strptime(obj.write_date, '%Y-%m-%d %H:%M:%S')
        else:
            return datetime.strptime(obj.create_date, '%Y-%m-%d %H:%M:%S')

    @api.model
    def getUserSign(self, userId):
        """
            get the user name
        """
        userType = self.env['res.users']
        uiUser = userType.browse(userId)
        return uiUser.name

    @api.multi
    def _getbyrevision(self, name, revision):
        result = False
        for result in self.search([('name', '=', name), ('revisionid', '=', revision)]):
            return result
        return result

    @api.model
    def getCheckedOut(self, oid, default=None):
        checkoutType = self.env['plm.checkout']
        checkoutBrwsList = checkoutType.search([('documentid', '=', oid)])
        for checkOutBrws in checkoutBrwsList:
            return(checkOutBrws.documentid.name,
                   checkOutBrws.documentid.revisionid,
                   self.getUserSign(checkOutBrws.userid.id),
                   checkOutBrws.hostname)
        return False

    @api.model
    def _file_delete(self, fname):
        '''
            Delete file only if is not saved on plm.backupdoc
        '''
        backupDocBrwsList = self.env['plm.backupdoc'].search([('existingfile', '=', fname)])
        if not backupDocBrwsList:
            return super(PlmDocument, self)._file_delete(fname)

    @api.model
    def GetNextDocumentName(self, documentName):
        '''
            Return a new name due to sequence next number.
        '''
        nextDocNum = self.env['ir.sequence'].next_by_code('plm.document.progress')
        return documentName + '-' + nextDocNum

    @api.model
    def canBeSavedClient(self, documentValues={}, returnCode=False):
        docName = documentValues.get('name')
        docRev = documentValues.get('revisionid')
        for docBrws in self.search([('name', '=', docName),
                                    ('revisionid', '=', docRev)
                                    ]):
            return docBrws.canBeSaved(False, returnCode=returnCode)
        if returnCode:
            return True, _('Document %r with revision %r not present in Odoo.') % (docName, docRev), 'NO_ERROR'
        return True, _('Document %r with revision %r not present in Odoo.') % (docName, docRev)

    @api.model
    def canBeSaved(self, raiseError=False, returnCode=False):
        """
        check if the document can be saved and raise exception in case is not possible
        """
        outMessage = ''
        outCode = 'NO_ERROR'
        if self.state in ['released', 'obsoleted']:
            outMessage = _("Document is released and cannot be saved")
            outCode = 'DOC_RELEASED'
            if raiseError:
                raise UserError(outMessage)
        checkOutObject = self.getCheckOutObject()
        if checkOutObject:
            if checkOutObject.userid.id != self.env.uid:
                outMessage = _("Document is Check-Out from User %r", checkOutObject.name)
                outCode = 'DOC_CHECKOUT_FROM_USER'
                if raiseError:
                    raise UserError(outMessage)
        else:
            outMessage = _("Document in check-In unable to save!")
            outCode = 'DOC_CHECKIN'
            if raiseError:
                raise UserError(outMessage)

        def returnTuple():
            if len(outMessage) > 0:
                return False, outMessage
            return True, ''
        if returnCode:
            return returnTuple() + (outCode,)
        return returnTuple()

    @api.model
    def getCheckOutObject(self):
        checkoutIDs = self.env['plm.checkout'].search([('documentid', '=', self.id)])
        for checkoutID in checkoutIDs:
            return checkoutID
        return None

    @api.model
    def saveStructure(self, arguments):
        """
        save the structure passed
        self['FILE_PATH'] = ''
        self['PDF_PATH'] = ''
        self['PRODUCT_ATTRIBUTES'] = []
        self['DOCUMENT_ATTRIBUTES'] = []
        self['RELATION_ATTRIBUTES'] = []
        self['RELATIONS'] = [] # tutte le relazioni vanno qui ma devo metterci un attributo che mi identifica il tipo
                                # 2d2d 3d3d 3d2d o niente
        self['DOCUMENT_DATE'] = None
        """
        start = time.time()
        cPickleStructure, hostName, hostPws = arguments
        documentAttributes = {}
        documentRelations = {}
        productAttributes = {}
        productRelations = {}
        productDocumentRelations = {}
        objStructure = json.loads(cPickleStructure)

        documentAttribute = objStructure.get('DOCUMENT_ATTRIBUTES', {})
        if documentAttribute:
            for brwItem in self.search([('name', '=', documentAttribute.get('name', '')),
                                        ('revisionid', '=', documentAttribute.get('revisionid', -1))]):
                brwItem.canBeSaved(raiseError=True)

        def populateStructure(parentItem=False, structure={}):
            documentId = False
            productId = False
            createBom = structure.get('CREATE_BOM', True)
            documentProperty = structure.get('DOCUMENT_ATTRIBUTES', False)
            if documentProperty and structure.get('FILE_PATH', False):
                documentId = id(documentProperty)
                documentAttributes[documentId] = documentProperty
            productProperty = structure.get('PRODUCT_ATTRIBUTES', False)
            if productProperty:
                productId = id(productProperty)
                productAttributes[productId] = productProperty
            if productId and documentId:
                listRelated = productDocumentRelations.get(productId, [])
                listRelated.append(documentId)
                productDocumentRelations[productId] = listRelated
            if parentItem:
                parentDocumentId, parentProductId = parentItem
                relationAttributes = structure.get('MRP_ATTRIBUTES', {})
                childRelations = documentRelations.get(parentDocumentId, [])
                childRelations.append((documentId, relationAttributes.get('TYPE', '')))
                if parentDocumentId:
                    documentRelations[parentDocumentId] = list(set(childRelations))
                if parentProductId and createBom: # Case of part - assembly
                    if not documentId:
                        documentId = parentDocumentId
                    itemTuple = (productId, documentId, relationAttributes)
                    listItem = productRelations.get(parentProductId, [])
                    listItem.append(itemTuple)
                    productRelations[parentProductId] = listItem
                else:   # Case of drawing - model relation
                    if productId and parentDocumentId:
                        listRelated = productDocumentRelations.get(productId, [])
                        listRelated.append(parentDocumentId)
                        productDocumentRelations[productId] = listRelated
            for subStructure in structure.get('RELATIONS', []):
                populateStructure((documentId, productId), subStructure)
        populateStructure(structure=objStructure)

        # Save the document
        logging.info("Savind Document")
        alreadyEvaluated = []
        for documentAttribute in documentAttributes.values():
            documentAttribute['TO_UPDATE'] = False
            docBrws = False
            for brwItem in self.search([('name', '=', documentAttribute.get('name')),
                                        ('revisionid', '=', documentAttribute.get('revisionid'))]):
                if brwItem.id in alreadyEvaluated:
                    docBrws = brwItem   # To skip creation
                    documentAttribute['TO_UPDATE'] = False  # To skip same document preview/pdf uploading by the client
                    break
                if brwItem.state not in ['released', 'obsoleted']:
                    if brwItem.needUpdate():
                        brwItem.write(documentAttribute)
                        documentAttribute['TO_UPDATE'] = True
                docBrws = brwItem
                alreadyEvaluated.append(docBrws.id)
            if not docBrws:
                docBrws = self.create(documentAttribute)
                alreadyEvaluated.append(docBrws.id)
                docBrws.checkout(hostName, hostPws)
                documentAttribute['TO_UPDATE'] = True
            documentAttribute['id'] = docBrws.id

        # Save the product
        # Save product - document relation
        logging.info("Saving Product")
        productsEvaluated = []
        productTemplate = self.env['product.product']
        for refId, productAttribute in productAttributes.items():
            linkedDocuments = set()
            for refDocId in productDocumentRelations.get(refId, []):
                linkedDocuments.add((4, documentAttributes[refDocId].get('id', 0)))
            prodBrws = False
            for brwItem in productTemplate.search([('engineering_code', '=', productAttribute.get('engineering_code')),
                                                   ('engineering_revision', '=', productAttribute.get('engineering_revision'))]):
                if brwItem.id in productsEvaluated:
                    prodBrws = brwItem
                    break
                if brwItem.state not in ['released', 'obsoleted']:
                    brwItem.write(productAttribute)
                prodBrws = brwItem
                productsEvaluated.append(brwItem.id)
                break
            if not prodBrws:
                if not productAttribute.get('name', False):
                    productAttribute['name'] = productAttribute.get('engineering_code', False)
                if not productAttribute.get('engineering_code', False):     # I could have a document without component, so not create product
                    continue
                prodBrws = productTemplate.create(productAttribute)
                productsEvaluated.append(prodBrws.id)
            if linkedDocuments:
                prodBrws.write({'linkeddocuments': list(linkedDocuments)})
            productAttribute['id'] = prodBrws.id

        # Save the document relation
        logging.info("Saving Document Relations")
        documentRelationTemplate = self.env['plm.document.relation']
        createdDocRels = []
        for parentId, childrenRelations in documentRelations.items():
            trueParentId = documentAttributes[parentId].get('id', 0)
            for objBrw in documentRelationTemplate.search([('parent_id', '=', trueParentId)]):
                found = False
                for childId, relationType in childrenRelations:
                    trueChildId = documentAttributes.get(childId, {}).get('id', 0)
                    if objBrw.parent_id.id == trueParentId and objBrw.child_id.id == trueChildId and objBrw.link_kind == relationType:
                        found = True
                        key = '%s_%s_%s' % (trueParentId, trueChildId, relationType)
                        if key in createdDocRels:
                            continue
                        createdDocRels.append(key)
                        break
                if not found:   # Line removed from previous save
                    objBrw.unlink()
            for childId, relationType in childrenRelations:
                trueChildId = documentAttributes.get(childId, {}).get('id', 0)
                key = '%s_%s_%s' % (trueParentId, trueChildId, relationType)
                if key in createdDocRels:
                    continue
                createdDocRels.append(key)
                try:
                    documentRelationTemplate.create({'parent_id': trueParentId,
                                                     'child_id': trueChildId,
                                                     'link_kind': relationType})
                except Exception, ex:
                    logging.error(ex)
                    raise ex
        # Save the product relation
        domain = [('state', 'in', ['installed', 'to upgrade', 'to remove']), ('name', '=', 'plm_engineering')]
        apps = self.env['ir.module.module'].sudo().search_read(domain, ['name'])
        bomType = 'normal'
        if apps:
            bomType = 'ebom'
        logging.info("Saving Product Relations")
        mrpBomTemplate = self.env['mrp.bom']
        for parentId, childRelations in productRelations.items():
            trueParentId = productAttributes[parentId].get('id')
            brwProduct = productTemplate.search([('id', '=', trueParentId)])
            productTempId = brwProduct.product_tmpl_id.id
            brwBoml = mrpBomTemplate.search([('product_tmpl_id', '=', productTempId)])
            if not brwBoml:
                brwBoml = mrpBomTemplate.create({'product_tmpl_id': productTempId,
                                                 'type': bomType})
            # delete rows
            for _, documentId, _ in childRelations:
                trueDocumentId = documentAttributes.get(documentId, {}).get('id', 0)
                if trueDocumentId:  # seems strange this .. but i will delete only the bom with the right source id
                    for brwBom in brwBoml:
                        brwBom.deleteChildRow(trueDocumentId)
                    break
            # add rows
            for childId, documentId, relationAttributes in childRelations:
                if not (childId and documentId):
                    logging.warning("Bad relation request %r, %r" % (childId, documentId))
                    continue
                trueChildId = productAttributes[childId].get('id')
                trueDocumentId = documentAttributes[documentId].get('id')
                brwBom.addChildRow(trueChildId, trueDocumentId, relationAttributes, bomType)
        jsonify = json.dumps(objStructure)
        end = time.time()
        logging.debug("Time Spend For save structure is: %s" % (str(end - start)))
        return jsonify

    @api.model
    def checkout(self, hostName, hostPws):
        """
        check out the current document
        """
        if self.is_checkout:
            raise UserError(_("Unable to check-Out a document that is already checked id by user %r" % self.checkout_user))
        if self.state in ['released', 'obsoleted']:
            raise UserError(_("Unable to check-Outcheck-Out a document that is in state %r" % self.state))
        values = {'userid': self.env.uid,
                  'hostname': hostName,
                  'hostpws': hostPws,
                  'documentid': self.id}
        self.env['plm.checkout'].create(values)

    @api.model
    def needUpdate(self):
        """
        check if the file need to be updated
        """
        checkoutIds = self.env['plm.checkout'].search([('documentid', '=', self.id),
                                                       ('userid', '=', self.env.uid)])
        for _brw in checkoutIds:
            return True
        return False

    @api.multi
    def getDocumentInfos(self):
        '''
            Document infos for clone/revision procedure
        '''
        return {'name': self.name or '',
                'revisionid': self.revisionid,
                'description': self.description or '',
                'desc_modify': self.desc_modify or '',
                'doc_type': self.document_type,
                'datas_fname': self.datas_fname,
                '_id': self.id,
                'can_revise': self.canBeRevised(),
                }

    @api.model
    def getCloneRevisionStructure(self, values=[]):
        if not values:
            return {}

    @api.multi
    def canBeRevised(self):
        for docBrws in self:
            if docBrws.state == 'released' and docBrws.ischecked_in():
                return True
        return False

PlmDocument()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
