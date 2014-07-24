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
import os, stat
import logging
import time
from datetime import datetime

from openerp.osv import osv, fields
from openerp.osv.orm import except_orm
from openerp.tools.translate import _
import openerp.tools as tools

# To be adequated to plm.component class states
USED_STATES=[('draft','Draft'),('confirmed','Confirmed'),('released','Released'),('undermodify','UnderModify'),('obsoleted','Obsoleted')]
USEDIC_STATES=dict(USED_STATES)
#STATEFORRELEASE=['confirmed']
#STATESRELEASABLE=['confirmed','released','undermodify','UnderModify']

def random_name():
    random.seed()
    d = [random.choice(string.ascii_letters) for x in xrange(20) ]
    return ("".join(d))

def create_directory(path):
    dir_name = random_name()
    path = os.path.join(path,dir_name)
    os.makedirs(path)
    return dir_name

class plm_document(osv.osv):
    _name = 'plm.document'
    _table = 'plm_document'
    _inherit = 'ir.attachment'

    def _is_checkedout_for_me(self, cr, uid, oid, context=None):
        """
            Get if given document (or its latest revision) is checked-out for the requesting user
        """
        act=False
        lastDoc=self._getlastrev(cr, uid, [oid], context)
        checkType=self.pool.get('plm.checkout')
        docIDs=checkType.search(cr, uid, [('documentid','=',lastDoc[0])])
        for docID in docIDs:
            objectCheck = checkType.browse(cr, uid, docID)
            if objectCheck.userid.id==uid:
                act=True
                break
        return act

    def _getlastrev(self, cr, uid, ids, context=None):
        result = []
        for objDoc in self.browse(cr, uid, ids, context=context):
            docIds=self.search(cr,uid,[('name','=',objDoc.name)],order='revisionid',context=context)
            docIds.sort()   # Ids are not surely ordered, but revision are always in creation order.
            result.append(docIds[len(docIds)-1])
        return list(set(result))
            
    def _data_get_files(self, cr, uid, ids, listedFiles=([],[]), forceFlag=False, context=None):
        """
            Get Files to return to Client
        """
        result = []
        datefiles,listfiles=listedFiles
        for objDoc in self.browse(cr, uid, ids, context=context):
            timeDoc=self.getLastTime(cr,uid,objDoc.id)
            timeSaved=time.mktime(timeDoc.timetuple())
            try:
                isCheckedOutToMe=self._is_checkedout_for_me(cr, uid, objDoc.id, context)
                if not(objDoc.datas_fname in listfiles):
                    if (not objDoc.store_fname) and (objDoc.db_datas):
                        value = objDoc.db_datas
                    else:
                        value = file(os.path.join(self._get_filestore(cr), objDoc.store_fname), 'rb').read()
                    result.append((objDoc.id, objDoc.datas_fname, base64.encodestring(value), isCheckedOutToMe, timeDoc))
                else:
                    if forceFlag:
                        isNewer=True
                    else:
                        timefile=time.mktime(datetime.strptime(str(datefiles[listfiles.index(objDoc.datas_fname)]),'%Y-%m-%d %H:%M:%S').timetuple())
                        isNewer=(timeSaved-timefile)>5
                    if (isNewer and not(isCheckedOutToMe)):
                        if (not objDoc.store_fname) and (objDoc.db_datas):
                            value = objDoc.db_datas
                        else:
                            value = file(os.path.join(self._get_filestore(cr), objDoc.store_fname), 'rb').read()
                        result.append((objDoc.id, objDoc.datas_fname, base64.encodestring(value), isCheckedOutToMe, timeDoc))
                    else:
                        result.append((objDoc.id,objDoc.datas_fname,False, isCheckedOutToMe, timeDoc))
            except Exception, ex:
                logging.error("_data_get_files : Unable to access to document ("+str(objDoc.name)+"). Error :" + str(ex))
                result.append((objDoc.id,objDoc.datas_fname,False, True, self.getServerTime(cr, uid, ids)))
        return result
            
    def _data_get(self, cr, uid, ids, name, arg, context):
        result = {}
        value=False
        for objDoc in self.browse(cr, uid, ids, context=context):
            if not objDoc.store_fname:
                value=objDoc.db_datas
                if not value or len(value)<1:
                    raise osv.except_osv(_('Stored Document Error'), _("Document %s - %s cannot be accessed" %(str(objDoc.name),str(objDoc.revisionid))))
            else:
                filestore=os.path.join(self._get_filestore(cr), objDoc.store_fname)
                if os.path.exists(filestore):
                    value = file(filestore, 'rb').read()
            if value and len(value)>0:
                result[objDoc.id] = base64.encodestring(value)
            else:
                result[objDoc.id] = ''
        return result

    def _data_set(self, cr, uid, oid, name, value, args=None, context=None):
        oiDocument=self.browse(cr, uid, oid, context)
        if not value:
            filename = oiDocument.store_fname
            try:
                os.unlink(os.path.join(self._get_filestore(cr), filename))
            except:
                pass
            cr.execute('update plm_document set store_fname=NULL WHERE id=%s', (oid,) )
            return True
        #if (not context) or context.get('store_method','fs')=='fs':
        try:
            printout=False
            preview=False
            if oiDocument.printout:
                printout=oiDocument.printout
            if oiDocument.preview:
                preview=oiDocument.preview
            db_datas=b''                    # Clean storage field. 
            fname,filesize=self._manageFile(cr,uid,oid,binvalue=value,context=context)
            cr.execute('update plm_document set store_fname=%s,file_size=%s,db_datas=%s where id=%s', (fname,filesize,db_datas,oid))
            self.pool.get('plm.backupdoc').create(cr,uid, {
                                          'userid':uid,
                                          'existingfile':fname,
                                          'documentid':oid,
                                          'printout': printout,
                                          'preview': preview
                                         }, context=context)

            return True
        except Exception,ex :
            raise except_orm(_('Error in _data_set'), str(ex))

    def _explodedocs(self, cr, uid, oid, kind, listed_documents=[], recursion=True):
        result=[]
        if (oid in listed_documents):
            return result
        documentRelation=self.pool.get('plm.document.relation')
        docRelIds=documentRelation.search(cr,uid,[('parent_id', '=',oid),('link_kind', '=',kind)])
        if len(docRelIds)==0:
            return result
        children=documentRelation.browse(cr,uid,docRelIds)
        for child in children:
            if recursion:
                listed_documents.append(oid)
                result.extend(self._explodedocs(cr, uid, child.child_id.id, kind, listed_documents,recursion))
            result.append(child.child_id.id)
        return result

    def _relateddocs(self, cr, uid, oid, kind, listed_documents=[], recursion=True):
        result=[]
        if (oid in listed_documents):
            return result
        documentRelation=self.pool.get('plm.document.relation')
        docRelIds=documentRelation.search(cr,uid,[('child_id', '=',oid),('link_kind', '=',kind)])
        if len(docRelIds)==0:
            return result
        children=documentRelation.browse(cr,uid,docRelIds)
        for child in children:
            if recursion:
                listed_documents.append(oid)
                result.extend(self._relateddocs(cr, uid, child.parent_id.id, kind, listed_documents, recursion))
            if child.parent_id.id:
                result.append(child.parent_id.id)
        return list(set(result))

    def _relatedbydocs(self, cr, uid, oid, kind, listed_documents=[], recursion=True):
        result=[]
        if (oid in listed_documents):
            return result
        documentRelation=self.pool.get('plm.document.relation')
        docRelIds=documentRelation.search(cr,uid,[('parent_id', '=',oid),('link_kind', '=',kind)])
        if len(docRelIds)==0:
            return result
        children=documentRelation.browse(cr,uid,docRelIds)
        for child in children:
            if recursion:
                listed_documents.append(oid)
                result.extend(self._relatedbydocs(cr, uid, child.child_id.id, kind, listed_documents, recursion))
            if child.child_id.id:
                result.append(child.child_id.id)
        return list(set(result))

    def _data_check_files(self, cr, uid, ids, listedFiles=(), forceFlag=False, context=None):
        result = []
        datefiles,listfiles=listedFiles
        for objDoc in self.browse(cr, uid, list(set(ids)), context=context):
            timeDoc=self.getLastTime(cr,uid,objDoc.id)
            timeSaved=time.mktime(timeDoc.timetuple())
            isCheckedOutToMe=self._is_checkedout_for_me(cr, uid, objDoc.id, context)
            if (objDoc.datas_fname in listfiles):
                if forceFlag:
                    isNewer = True
                else:
                    timefile=time.mktime(datetime.strptime(str(datefiles[listfiles.index(objDoc.datas_fname)]),'%Y-%m-%d %H:%M:%S').timetuple())
                    isNewer=(timeSaved-timefile)>5
                collectable = isNewer and not(isCheckedOutToMe)
            else:
                collectable = True
            if (objDoc.file_size<1) and (objDoc.datas):
                objDoc.file_size=len(objDoc.datas)
            result.append((objDoc.id, objDoc.datas_fname, objDoc.file_size, collectable, isCheckedOutToMe, timeDoc))
        return list(set(result))
            
    def copy(self,cr,uid,oid,defaults={},context=None):
        """
            Overwrite the default copy method
        """
        #get All document relation 
        documentRelation=self.pool.get('plm.document.relation')
        docRelIds=documentRelation.search(cr,uid,[('parent_id', '=',oid)],context=context)
        if len(docRelIds)==0:
            docRelIds=False 
        previous_name=self.browse(cr,uid,oid,context=context).name
        if not 'name' in defaults:
            new_name='Copy of %s'%previous_name
            l=self.search(cr,uid,[('name','=',new_name)],order='revisionid',context=context)
            if len(l)>0:
                new_name='%s (%s)'%(new_name,len(l)+1)
            defaults['name']=new_name
        #manage copy of the file
        fname,filesize=self._manageFile(cr,uid,oid,context=context)
        #assign default value
        defaults['store_fname']=fname
        defaults['file_size']=filesize
        defaults['state']='draft'
        defaults['writable']=True
        newID=super(plm_document,self).copy(cr,uid,oid,defaults,context=context)
        if (newID):
            self.wf_message_post(cr, uid, [newID], body=_('Copied starting from : %s.' %previous_name))
        if docRelIds:
            # create all the document relation
            brwEnts=documentRelation.browse(cr,uid,docRelIds,context=context)
            for brwEnt in brwEnts:
                documentRelation.create(cr,uid, {
                                          'parent_id':newID,
                                          'child_id':brwEnt.child_id.id,
                                          'configuration':brwEnt.configuration,
                                          'link_kind':brwEnt.link_kind,
                                         }, context=context)
        return newID 

    def _manageFile(self,cr,uid, oid, binvalue=None, context=None):
        """
            use given 'binvalue' to save it on physical repository and to read size (in bytes).
        """
        path = self._get_filestore(cr)
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except:
                raise osv.except_osv(_('Document Error'), _("Permission denied or directory %s cannot be created." %(str(path))))
        
        flag = None
        # This can be improved
        for dirs in os.listdir(path):
            if os.path.isdir(os.path.join(path,dirs)) and len(os.listdir(os.path.join(path,dirs)))<4000:
                flag = dirs
                break
        if binvalue==None:
            fileStream=self._data_get(cr, uid, [oid], name=None, arg=None, context=context)
            binvalue=fileStream[fileStream.keys()[0]]
        
        flag = flag or create_directory(path)
        filename = random_name()
        fname = os.path.join(path, flag, filename)
        fobj = file(fname,'wb')
        value = base64.decodestring(binvalue)
        fobj.write(value)
        fobj.close()
        return (os.path.join(flag,filename),len(value))

    def _iswritable(self, cr, user, oid):
        checkState=('draft')
        if not oid.engineering_writable:
            logging.warning("_iswritable : Part ("+str(oid.engineering_code)+"-"+str(oid.engineering_revision)+") not writable.")
            return False
        if not oid.state in checkState:
            logging.warning("_iswritable : Part ("+str(oid.engineering_code)+"-"+str(oid.engineering_revision)+") in status ; "+str(oid.state)+".")
            return False
        if oid.engineering_code == False:
            logging.warning("_iswritable : Part ("+str(oid.name)+"-"+str(oid.engineering_revision)+") without Engineering P/N.")
            return False
        return True  
    
    def newVersion(self,cr,uid,ids,context=None):
        """
            create a new version of the document (to WorkFlow calling)
        """
        if self.newRevision(cr,uid,ids,context=context)!=None:
            return True 
        return False 

    def NewRevision(self,cr,uid,ids,context=None):
        """
            create a new revision of the document
        """
        newID=None
        for tmpObject in self.browse(cr, uid, ids, context=context):
            latestIDs=self.GetLatestIds(cr, uid,[(tmpObject.name,tmpObject.revisionid,False)], context=context)
            for oldObject in self.browse(cr, uid, latestIDs, context=context):
                self.write(cr,uid,[oldObject.id],{'state':'undermodify',} ,context=context,check=False)
                defaults={}
                defaults['name']=oldObject.name
                defaults['revisionid']=int(oldObject.revisionid)+1
                defaults['writable']=True
                defaults['state']='draft'
                newID=super(plm_document,self).copy(cr,uid,oldObject.id,defaults,context=context)
                self.wf_message_post(cr, uid, [oldObject.id], body=_('Created : New Revision.'))
                break
            break
        return (newID, defaults['revisionid']) 
    
    def Clone(self, cr, uid, oid, defaults={}, context=None):
        """
            create a new revision of the document
        """
        defaults={}
        exitValues={}
        newID=self.copy(cr,uid,oid,defaults,context)
        if newID != None:
            newEnt=self.browse(cr,uid,newID,context=context)
            exitValues['_id']=newID
            exitValues['name']=newEnt.name
            exitValues['revisionid']=newEnt.revisionid
        return exitValues
    
    def CheckSaveUpdate(self, cr, uid, documents, default=None, context=None):
        """
            Save or Update Documents
        """
        retValues=[]
        for document in documents:
            hasSaved=False
            if not ('name' in document) or (not 'revisionid' in document):
                document['documentID']=False
                document['hasSaved']=hasSaved
                continue
            existingID=self.search(cr,uid,[
                                           ('name','=',document['name'])
                                          ,('revisionid','=',document['revisionid'])],order='revisionid')
            if not existingID:
                hasSaved=True
            else:
                existingID=existingID[0]
                objDocument=self.browse(cr, uid, existingID, context=context)
#               logging.info("CheckSaveUpdate : time db : %s time file : %s" %(str(self.getLastTime(cr,uid,existingID).strftime('%Y-%m-%d %H:%M:%S')), str(document['lastupdate'])))
                if self.getLastTime(cr,uid,existingID)<datetime.strptime(str(document['lastupdate']),'%Y-%m-%d %H:%M:%S'):
                    if objDocument.writable:
                        hasSaved=True
            document['documentID']=existingID
            document['hasSaved']=hasSaved
            retValues.append(document)
        return retValues 

    def SaveOrUpdate(self, cr, uid, documents, default=None, context=None):
        """
            Save or Update Documents
        """
        retValues=[]
        for document in documents:
            hasSaved=False
            hasUpdated=False
            if not ('name' in document) or (not 'revisionid' in document):
                document['documentID']=False
                document['hasSaved']=hasSaved
                document['hasUpdated']=hasUpdated
                continue
            existingID=self.search(cr,uid,[
                                           ('name','=',document['name'])
                                          ,('revisionid','=',document['revisionid'])],order='revisionid')
            if not existingID:
                existingID=self.create(cr,uid,document)
                hasSaved=True
            else:
                existingID=existingID[0]
                objDocument=self.browse(cr, uid, existingID, context=context)
#                logging.info("SaveOrUpdate : time db : %s time file : %s" %(str(self.getLastTime(cr,uid,existingID).strftime('%Y-%m-%d %H:%M:%S')), str(document['lastupdate'])))
                if self.getLastTime(cr,uid,existingID)<datetime.strptime(str(document['lastupdate']),'%Y-%m-%d %H:%M:%S'):
                    if self._iswritable(cr,uid,objDocument):
                        del(document['lastupdate'])
                        if not self.write(cr,uid,[existingID], document , context=context, check=True):
                            raise osv.except_osv(_('Update Document Error'), _("Document %s - %s cannot be updated" %(str(document['name']), str(document['revisionid']))))
                        hasSaved=True
            document['documentID']=existingID
            document['hasSaved']=hasSaved
            document['hasUpdated']=hasUpdated
            retValues.append(document)
        return retValues 

    def RegMessage(self, cr, uid, request, default=None, context=None):
        """
            Registers a message for requested document
        """
        oid, message = request
        self.wf_message_post(cr, uid, [oid], body=_(message))
        return False

    def UpdateDocuments(self, cr, uid, documents, default=None, context=None):
        """
            Save or Update Documents
        """
        ret=True
        for document in documents:
            oid=document['documentID']
            del(document['documentID'])
            ret=ret and self.write(cr,uid,[oid], document , context=context, check=True)
        return ret 

    def CleanUp(self, cr, uid, ids, default=None, context=None):
        """
            Remove faked documents
        """
        cr.execute('delete from plm_document where store_fname=NULL')
        return True 

    def QueryLast(self, cr, uid, request=([],[]), default=None, context=None):
        """
            Query to return values based on columns selected.
        """
        objId=False
        expData=[]
        queryFilter, columns = request        
        if len(columns)<1:
            return expData
        if 'revisionid' in queryFilter:
            del queryFilter['revisionid']
        allIDs=self.search(cr,uid,queryFilter,order='revisionid',context=context)
        if len(allIDs)>0:
            allIDs.sort()
            tmpData=self.export_data(cr, uid, allIDs, columns)
            if 'datas' in tmpData:
                expData=tmpData['datas']
        return expData

    def ischecked_in(self, cr, uid, ids, context=None):
        """
            Check if a document is checked-in 
        """
        documents=self.browse(cr, uid, ids, context=context)
        checkoutType=self.pool.get('plm.checkout')
             
        for document in documents:
            if checkoutType.search(cr, uid, [('documentid','=',document.id)], context=context):
                logging.warning(_("The document %s - %s has not checked-in" %(str(document.name),str(document.revisionid))))
                return False
        return True
 
    def wf_message_post(self,cr,uid,ids,body='',context=None):
        """
            Writing messages to follower, on multiple objects
        """
        if not (body==''):
            for id in ids:
                self.message_post(cr, uid, [id], body=_(body))

    def action_draft(self, cr, uid, ids, *args):
        """
            release the object
        """
        defaults={}
        defaults['writable']=True
        defaults['state']='draft'
        objId = self.write(cr, uid, ids, defaults, check=False)
        if (objId):
            self.wf_message_post(cr, uid, ids, body=_('Status moved to: %s.' %(USEDIC_STATES[defaults['state']])))
        return objId

    def action_correct(self, cr, uid, ids, *args):
        """
            release the object
        """
        return self.action_draft(cr, uid, ids, *args)

    def action_confirm(self,cr,uid,ids,context=None):
        """
            action to be executed for Draft state
        """
        defaults={}
        defaults['writable']=False
        defaults['state']='confirmed'
        if self.ischecked_in(cr, uid, ids,context):
            objId = self.write(cr, uid, ids, defaults, context=context, check=False)
            if (objId):
                self.wf_message_post(cr, uid, ids, body=_('Status moved to: %s.' %(USEDIC_STATES[defaults['state']])))
            return objId
        return False
    
    def action_release(self, cr, uid, ids, *args):
        """
            release the object
        """
        defaults={}
        for oldObject in self.browse(cr, uid, ids, context=None):
            last_id=self._getbyrevision(cr, uid, oldObject.name, oldObject.revisionid-1)
            if last_id != None:
                defaults['writable']=False
                defaults['state']='obsoleted'
                self.write(cr, uid, [last_id], defaults, check=False)
                self.wf_message_post(cr, uid, [last_id], body=_('Status moved to: %s.' %(USEDIC_STATES[defaults['state']])))
        defaults['writable']=False
        defaults['state']='released'
        if self.ischecked_in(cr, uid, ids):
            objId = self.write(cr, uid, ids, defaults, check=False)
            if (objId):
                self.wf_message_post(cr, uid, ids, body=_('Status moved to: %s.' %(USEDIC_STATES[defaults['state']])))
            return objId
        return False

    def action_obsolete(self,cr,uid,ids,context=None):
        """
            obsolete the object
        """
        defaults={}
        defaults['writable']=False
        defaults['state']='obsoleted'
        if self.ischecked_in(cr, uid, ids,context):
            objId = self.write(cr, uid, ids, defaults, context=context, check=False)
            if (objId):
                self.wf_message_post(cr, uid, ids, body=_('Status moved to: %s.' %(USEDIC_STATES[defaults['state']])))
            return objId
        return False

    def action_reactivate(self,cr,uid,ids,context=None):
        """
            reactivate the object
        """
        defaults={}
        defaults['engineering_writable']=False
        defaults['state']='released'
        if self.ischecked_in(cr, uid, ids,context):
            objId = self.write(cr, uid, ids, defaults, context=context, check=False)
            if (objId):
                self.wf_message_post(cr, uid, ids, body=_('Status moved to:%s.' %(USEDIC_STATES[defaults['state']])))
            return objId
        return False

#   Overridden methods for this entity
    def _get_filestore(self, cr):
        dms_Root_Path=tools.config.get('document_path', os.path.join(tools.config['root_path'], 'filestore'))
        return os.path.join(dms_Root_Path, cr.dbname)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # Grab ids, bypassing 'count'
        ids = osv.osv.search(self,cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=False)
        if not ids:
            return 0 if count else []

        # Filter out documents that are in directories that the user is not allowed to read.
        # Must use pure SQL to avoid access rules exceptions (we want to remove the records,
        # not fail), and the records have been filtered in parent's search() anyway.
        cr.execute('SELECT id, parent_id from plm_document WHERE id in %s', (tuple(ids),))

        # cont a dict of parent -> attach
        parents = {}
        for attach_id, attach_parent in cr.fetchall():
            parents.setdefault(attach_parent, []).append(attach_id)
        parent_ids = parents.keys()

        # filter parents
        visible_parent_ids = self.pool.get('document.directory').search(cr, uid, [('id', 'in', list(parent_ids))])

        # null parents means allowed
        ids = parents.get(None,[])
        for parent_id in visible_parent_ids:
            ids.extend(parents[parent_id])

        return len(ids) if count else ids

    def write(self, cr, uid, ids, vals, context=None, check=True):
        checkState=('confirmed','released','undermodify','obsoleted')
        if check:
            for customObject in self.browse(cr,uid,ids,context=context):
                if customObject.state in checkState:
                    raise osv.except_osv(_('Edit Entity Error'), _("The active state does not allow you to make save action"))
                    return False
        return super(plm_document,self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        values={'state':'released',}
        checkState=('undermodify','obsoleted')
        for checkObj in self.browse(cr, uid, ids, context=context):
            existingID = self.search(cr, uid, [('name', '=', checkObj.name),('revisionid', '=', checkObj.revisionid-1)])
            if len(existingID)>0:
                oldObject=self.browse(cr, uid, existingID[0], context=context)
                if oldObject.state in checkState:
                    self.wf_message_post(cr, uid, [oldObject.id], body=_('Removed : Latest Revision.'))
                    if not self.write(cr, uid, [oldObject.id], values, context, check=False):
                        logging.warning("unlink : Unable to update state to old document ("+str(oldObject.name)+"-"+str(oldObject.revisionid)+").")
                        return False
        return super(plm_document,self).unlink(cr, uid, ids, context=context)

#   Overridden methods for this entity

#     def _check_duplication0(self, cr, uid, vals, ids=[], op='create'):
#         """
#             Overridden, due to revision id management, filename can be duplicated, 
#             because system has to manage several revisions of a document.
#         """
#         name = vals.get('name', False)
#         parent_id = vals.get('parent_id', False)
#         res_model = vals.get('res_model', False)
#         res_id = vals.get('res_id', 0)
#         revisionid = vals.get('revisionid', 0)
#         if op == 'write':
#             for thisfile in self.browse(cr, uid, ids, context=None): # FIXME fields_only
#                 if not name:
#                     name = thisfile.name
#                 if not parent_id:
#                     parent_id = thisfile.parent_id and thisfile.parent_id.id or False
#                 if not res_model:
#                     res_model = thisfile.res_model and thisfile.res_model or False
#                 if not res_id:
#                     res_id = thisfile.res_id and thisfile.res_id or 0
#                 if not revisionid:
#                     revisionid = thisfile.revisionid and thisfile.revisionid or 0
#                 res = self.search(cr, uid, [('id', '<>', thisfile.id), ('name', '=', name), ('parent_id', '=', parent_id), ('res_model', '=', res_model), ('res_id', '=', res_id), ('revisionid', '=', revisionid)])
#                 if len(res)>1:
#                     return False
#         if op == 'create':
#             res = self.search(cr, uid, [('name', '=', name), ('parent_id', '=', parent_id), ('res_id', '=', res_id), ('res_model', '=', res_model), ('revisionid', '=', revisionid)])
#             if len(res):
#                 return False
#         return True

    def _check_duplication(self, cr, uid, vals, ids=None, op='create'):
        SUPERUSER_ID = 1
        name=vals.get('name',False)
        parent_id=vals.get('parent_id',False)
        ressource_parent_type_id=vals.get('ressource_parent_type_id',False)
        ressource_id=vals.get('ressource_id',0)
        revisionid = vals.get('revisionid', 0)
        if op=='write':
            for directory in self.browse(cr, SUPERUSER_ID, ids):
                if not name:
                    name=directory.name
                if not parent_id:
                    parent_id=directory.parent_id and directory.parent_id.id or False
                # TODO fix algo
                if not ressource_parent_type_id:
                    ressource_parent_type_id=directory.ressource_parent_type_id and directory.ressource_parent_type_id.id or False
                if not ressource_id:
                    ressource_id=directory.ressource_id and directory.ressource_id or 0
                res=self.search(cr,uid,[('id','<>',directory.id),('name','=',name),('parent_id','=',parent_id),('ressource_parent_type_id','=',ressource_parent_type_id),('ressource_id','=',ressource_id), ('revisionid', '=', revisionid)])
                if len(res):
                    return False
        if op=='create':
            res = self.search(cr, SUPERUSER_ID, [('name','=',name),('parent_id','=',parent_id),('ressource_parent_type_id','=',ressource_parent_type_id),('ressource_id','=',ressource_id), ('revisionid', '=', revisionid)])
            if len(res):
                return False
        return True
    
    _columns = {
                'usedforspare': fields.boolean('Used for Spare',help="Drawings marked here will be used printing Spare Part Manual report."),
                'revisionid': fields.integer('Revision Index', required=True),
                'writable': fields.boolean('Writable'),
                'datas': fields.function(_data_get,method=True,fnct_inv=_data_set,string='File Content',type="binary"),
                'printout': fields.binary('Printout Content', help="Print PDF content."),
                'preview': fields.binary('Preview Content', help="Static preview."),
                'state':fields.selection(USED_STATES,'Status', help="The status of the product.", readonly="True", required=True),
    }    

    _defaults = {
                 'usedforspare': lambda *a: False,
                 'revisionid': lambda *a: 0,
                 'writable': lambda *a: True,
                 'state': lambda *a: 'draft',
    }

    _sql_constraints = [
        ('filename_unique', 'unique (name,revisionid)', 'File name has to be unique!') # qui abbiamo la sicurezza dell'univocita del nome file
    ]

    def CheckedIn(self, cr, uid, files, default=None, context=None):
        """
            Get checked status for requested files
        """
        retValues=[]
        def getcheckedfiles(files):
            res=[]
            for fileName in files:
                ids=self.search(cr,uid,[('datas_fname','=',fileName)],order='revisionid')
                if len(ids)>0:
                    ids.sort()
                    res.append([fileName,not(self._is_checkedout_for_me(cr, uid, ids[len(ids)-1], context))])
            return res
        
        if len(files)>0: # no files to process 
            retValues=getcheckedfiles(files)
        return retValues

    def GetUpdated(self,cr,uid,vals,context=None):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        docData, attribNames = vals
        ids=self.GetLatestIds(cr, uid, docData, context)
        return self.read(cr, uid, list(set(ids)), attribNames)

    def GetLatestIds(self,cr,uid,vals,context=None):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        ids=[]
        for docName, docRev, updateDate in vals:
            if updateDate:
                if docRev == None or docRev == False:
                    docIds=self.search(cr,uid,[('name','=',docName),('write_date','>',updateDate)],order='revisionid',context=context)
                    if len(docIds)>0:
                        ids.sort()
                        ids.append(docIds[len(ids)-1])
                else:
                    docIds=self.search(cr,uid,[('name','=',docName),('revisionid','=',docRev),('write_date','>',updateDate)],context=context)
                    if len(docIds)>0:
                        ids.extend(docIds)
            else:
                if docRev == None or docRev == False:
                    docIds=self.search(cr,uid,[('name','=',docName)],order='revisionid',context=context)
                    if len(docIds)>0:
                        ids.sort()
                        ids.append(docIds[len(ids)-1])
                else:
                    docIds=self.search(cr,uid,[('name','=',docName),('revisionid','=',docRev)],context=context)
                    if len(docIds)>0:
                        ids.extend(docIds)
        return list(set(ids))

    def CheckAllFiles(self, cr, uid, request, default=None, context=None):
        """
            Evaluate documents to return
        """
        forceFlag=False
        listed_models=[]
        listed_documents=[]
        oid, listedFiles, selection = request        
        if selection == False:
            selection=1
        if selection<0:
            forceFlag=True
            selection=selection*(-1)

        kind='LyTree'   # Get relations due to layout connected
        docArray=self._relateddocs(cr, uid, oid, kind, listed_documents)

        kind='HiTree'   # Get Hierarchical tree relations due to children
        modArray=self._explodedocs(cr, uid, oid, kind, listed_models)
        for item in docArray:
            if item not in modArray:
                modArray.append(item)
        docArray=modArray  
        if selection == 2:
            docArray=self._getlastrev(cr, uid, docArray, context)
        
        if not oid in docArray:
            docArray.append(oid)     # Add requested document to package
        return self._data_check_files(cr, uid, docArray, listedFiles, forceFlag, context)

    def GetSomeFiles(self, cr, uid, request, default=None, context=None):
        """
            Extract documents to be returned 
        """
        forceFlag=False
        ids, listedFiles, selection = request
        if selection == False:
            selection=1

        if selection<0:
            forceFlag=True
            selection=selection*(-1)

        if selection == 2:
            docArray=self._getlastrev(cr, uid, ids, context)
        else:
            docArray=ids
        return self._data_get_files(cr, uid, docArray, listedFiles, forceFlag, context)

    def GetAllFiles(self, cr, uid, request, default=None, context=None):
        """
            Extract documents to be returned 
        """
        forceFlag=False
        listed_models=[]
        listed_documents=[]
        modArray=[]
        oid, listedFiles, selection = request
        if selection == False:
            selection=1

        if selection<0:
            forceFlag=True
            selection=selection*(-1)

        kind='HiTree'                   # Get Hierarchical tree relations due to children
        docArray=self._explodedocs(cr, uid, oid, kind, listed_models)
        
        if not oid in docArray:
            docArray.append(oid)        # Add requested document to package
                
        for item in docArray:
            kind='LyTree'               # Get relations due to layout connected
            modArray.extend(self._relateddocs(cr, uid, item, kind, listed_documents))
            modArray.extend(self._explodedocs(cr, uid, item, kind, listed_documents))
            kind='RfTree'               # Get relations due to referred connected
            modArray.extend(self._relateddocs(cr, uid, item, kind, listed_documents))
            modArray.extend(self._explodedocs(cr, uid, item, kind, listed_documents))

        modArray.extend(docArray)
        docArray=list(set(modArray))    # Get unique documents object IDs

        if selection == 2:
            docArray=self._getlastrev(cr, uid, docArray, context)
        
        if not oid in docArray:
            docArray.append(oid)     # Add requested document to package
        return self._data_get_files(cr, uid, docArray, listedFiles, forceFlag, context)

    def GetRelatedDocs(self, cr, uid, ids, default=None, context=None):
        """
            Extract documents related to current one(s) (layouts, referred models, etc.)
        """
        related_documents=[]
        listed_documents=[]
        read_docs=[]
        for oid in ids:
            kind='RfTree'   # Get relations due to referred models
            read_docs.extend(self._relateddocs(cr, uid, oid, kind, listed_documents, False))
            read_docs.extend(self._relatedbydocs(cr, uid, oid, kind, listed_documents, False))

            kind='LyTree'   # Get relations due to layout connected
            read_docs.extend(self._relateddocs(cr, uid, oid, kind, listed_documents, False))
            read_docs.extend(self._relatedbydocs(cr, uid, oid, kind, listed_documents, False))
       
        documents=self.browse(cr, uid, read_docs, context=context)
        for document in documents:
            related_documents.append([document.id,document.name,document.preview])
        return related_documents

    def getServerTime(self, cr, uid, oid, default=None, context=None):
        """
            calculate the server db time 
        """
        return datetime.now()
    
    def getLastTime(self, cr, uid, oid, default=None, context=None):
        """
            get document last modification time 
        """
        obj = self.browse(cr, uid, oid, context=context)
        if(obj.write_date!=False):
            return datetime.strptime(obj.write_date,'%Y-%m-%d %H:%M:%S')
        else:
            return datetime.strptime(obj.create_date,'%Y-%m-%d %H:%M:%S')

    def getUserSign(self, cr, uid, oid, default=None, context=None):
        """
            get the user name
        """
        userType=self.pool.get('res.users')
        uiUser=userType.browse(cr,uid,uid,context=context)
        return uiUser.name

    def _getbyrevision(self, cr, uid, name, revision):
        result=None
        results=self.search(cr,uid,[('name','=',name),('revisionid','=',revision)])
        for result in results:
            break
        return result
    
    def getCheckedOut(self, cr, uid, oid, default=None, context=None):
        checkoutType=self.pool.get('plm.checkout')
        checkoutIDs=checkoutType.search(cr,uid,[('documentid', '=',oid)])
        for checkoutID in checkoutIDs:
            objDoc=checkoutType.browse(cr,uid,checkoutID)
            return(objDoc.documentid.name,objDoc.documentid.revisionid,self.getUserSign(cr,objDoc.userid.id,1),objDoc.hostname)
        return False

plm_document()


class plm_checkout(osv.osv):
    _name = 'plm.checkout'
    _columns = {
                'userid':fields.many2one('res.users', 'Related User', ondelete='cascade'), 
                'hostname':fields.char('hostname',size=64), 
                'hostpws':fields.char('PWS Directory',size=1024), 
                'documentid':fields.many2one('plm.document', 'Related Document', ondelete='cascade'), 
                'createdate':fields.datetime('Date Created', readonly=True)
    }
    _defaults = {
        'createdate': lambda self,cr,uid,ctx:time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _sql_constraints = [
        ('documentid', 'unique (documentid)', 'The documentid must be unique !') 
    ]

    def _adjustRelations(self, cr, uid, oids, userid=False):
        docRelType=self.pool.get('plm.document.relation')
        if userid:
            ids=docRelType.search(cr,uid,[('child_id','in',oids),('userid','=',False)])
        else:
            ids=docRelType.search(cr,uid,[('child_id','in',oids)])
        if ids:
            values={'userid':userid,}
            docRelType.write(cr, uid, ids, values)

    def create(self, cr, uid, vals, context=None):
        if context!=None and context!={}:
            return False
        documentType=self.pool.get('plm.document')
        docID=documentType.browse(cr, uid, vals['documentid'])
        values={'writable':True,}
        if not documentType.write(cr, uid, [docID.id], values):
            logging.warning("create : Unable to check-out the required document ("+str(docID.name)+"-"+str(docID.revisionid)+").")
            raise osv.except_osv(_('Check-Out Error'), _("Unable to check-out the required document ("+str(docID.name)+"-"+str(docID.revisionid)+")."))
            return False
        self._adjustRelations(cr, uid, [docID.id], uid)
        newID = super(plm_checkout,self).create(cr, uid, vals, context=context)   
        documentType.wf_message_post(cr, uid, [docID.id], body=_('Checked-Out'))
        return newID
         
    def unlink(self, cr, uid, ids, context=None):
        if context!=None and context!={}:
            if uid!=1:
                logging.warning("unlink : Unable to Check-In the required document.\n You aren't authorized in this context.")
                raise osv.except_osv(_('Check-In Error'), _("Unable to Check-In the required document.\n You aren't authorized in this context."))
                return False
        documentType=self.pool.get('plm.document')
        checkObjs=self.browse(cr, uid, ids, context=context)
        docids=[]
        for checkObj in checkObjs:
            checkObj.documentid.writable=False
            values={'writable':False,}
            docids.append(checkObj.documentid.id)
            if not documentType.write(cr, uid, [checkObj.documentid.id], values):
                logging.warning("unlink : Unable to check-in the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+").\n You can't change writable flag.")
                raise osv.except_osv(_('Check-In Error'), _("Unable to Check-In the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+").\n You can't change writable flag."))
                return False
        self._adjustRelations(cr, uid, docids, False)
        dummy = super(plm_checkout,self).unlink(cr, uid, ids, context=context)
        if dummy:
            documentType.wf_message_post(cr, uid, docids, body=_('Checked-In'))
        return dummy

plm_checkout()


class plm_document_relation(osv.osv):
    _name = 'plm.document.relation'
    _columns = {
                'parent_id':fields.many2one('plm.document', 'Related parent document', ondelete='cascade'), 
                'child_id':fields.many2one('plm.document', 'Related child document',  ondelete='cascade'),
                'configuration':fields.char('Configuration Name',size=1024),
                'link_kind': fields.char('Kind of Link',size=64, required=True),
                'create_date':fields.datetime('Date Created', readonly=True),
                'userid':fields.many2one('res.users', 'CheckOut User',readonly="True"), 
               }
    _defaults = {
                 'link_kind': lambda *a: 'HiTree',
                 'userid': lambda *a: False,
    }
    _sql_constraints = [
        ('relation_uniq', 'unique (parent_id,child_id,link_kind)', 'The Document Relation must be unique !') 
    ]

    def SaveStructure(self, cr, uid, relations, level=0, currlevel=0):
        """
            Save Document relations
        """
        def cleanStructure(relations):
            res={}
            cleanIds=[]
            for relation in relations:
                res['parent_id'],res['child_id'],res['configuration'],res['link_kind']=relation
                link=[('link_kind','=',res['link_kind'])]
                if (res['link_kind']=='LyTree') or (res['link_kind']=='RfTree'):
                    criteria=[('child_id','=',res['child_id'])]
                else:
                    criteria=[('parent_id','=',res['parent_id']),('child_id','=',res['child_id'])]
                cleanIds.extend(self.search(cr,uid,criteria+link))
            self.unlink(cr,uid,list(set(cleanIds)))

        def saveChild(relation):
            """
                save the relation 
            """
            try:
                res={}
                res['parent_id'],res['child_id'],res['configuration'],res['link_kind']=relation
                if (res['parent_id']!= None) and (res['child_id']!=None):
                    if (len(str(res['parent_id']))>0) and (len(str(res['child_id']))>0):
                        if not((res['parent_id'],res['child_id']) in savedItems):
                            savedItems.append((res['parent_id'],res['child_id']))
                            self.create(cr, uid, res)
                else:
                    logging.error("saveChild : Unable to create a relation between documents. One of documents involved doesn't exist. Arguments(" + str(relation) +") ")
                    raise Exception("saveChild: Unable to create a relation between documents. One of documents involved doesn't exist.")
            except Exception,ex:
                logging.error("saveChild : Unable to create a relation. Arguments (%s) Exception (%s)" %(str(relation), str(ex)))
                raise Exception("saveChild: Unable to create a relation.")
            
        savedItems=[]
        if len(relations)<1: # no relation to save 
            return False
        cleanStructure(relations)
        for relation in relations:
            saveChild(relation)
        return False

plm_document_relation()


class plm_backupdoc(osv.osv):
    _name = 'plm.backupdoc'
    _columns = {
                'userid':fields.many2one('res.users', 'Related User', ondelete='cascade'), 
                'createdate':fields.datetime('Date Created', readonly=True),
                'existingfile':fields.char('Physical Document Location',size=1024), 
                'documentid':fields.many2one('plm.document', 'Related Document', ondelete='cascade'), 
                'revisionid': fields.related('documentid','revisionid',type="integer",relation="plm.document",string="Revision",store=False),
                'state': fields.related('documentid','state',type="char",relation="plm.document",string="Status",store=False),
                'printout': fields.binary('Printout Content'),
                'preview': fields.binary('Preview Content'),
    }
    _defaults = {
        'createdate': lambda self,cr,uid,ctx:time.strftime("%Y-%m-%d %H:%M:%S")
    }
        
    def unlink(self, cr, uid, ids, context=None):
        committed=False
        if context!=None and context!={}:
            if uid!=1:
                logging.warning("unlink : Unable to remove the required documents. You aren't authorized in this context.")
                raise osv.except_osv(_('Backup Error'), _("Unable to remove the required document.\n You aren't authorized in this context."))
                return False
        documentType=self.pool.get('plm.document')
        checkObjs=self.browse(cr, uid, ids, context=context)
        for checkObj in checkObjs:
            if not int(checkObj.documentid):
                return super(plm_backupdoc,self).unlink(cr, uid, ids, context=context)
            currentname=checkObj.documentid.store_fname
            if checkObj.existingfile != currentname:
                fullname=os.path.join(documentType._get_filestore(cr),checkObj.existingfile)
                if os.path.exists(fullname):
                    if os.path.exists(fullname):
                        os.chmod(fullname, stat.S_IWRITE)
                        os.unlink(fullname)
                        committed=True
                else:
                    logging.warning("unlink : Unable to remove the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+") from backup set. You can't change writable flag.")
                    raise osv.except_osv(_('Check-In Error'), _("Unable to remove the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+") from backup set.\n It isn't a backup file, it's original current one."))
        if committed:
            return super(plm_backupdoc,self).unlink(cr, uid, ids, context=context)
        else:
            return False

    def action_restore_document(self, cr, uid, ids, context=None):
        committed=False
        if context!=None and context!={}:
            if uid!=1:
                logging.warning("unlink : Unable to remove the required documents.\n You aren't authorized in this context.")
                raise osv.except_osv(_('Backup Error'), _("Unable to remove the required document.\n You aren't authorized in this context."))
                return False
        documentType=self.pool.get('plm.document')
        checkObj=self.browse(cr, uid, context['active_id'])
        objDoc=documentType.browse(cr, uid, checkObj.documentid.id)
        if objDoc.state=='draft' and documentType.ischecked_in(cr, uid, ids, context):
            if checkObj.existingfile != objDoc.store_fname:
                committed=documentType.write(cr, uid, [objDoc.id], {'store_fname':checkObj.existingfile,'printout':checkObj.printout,'preview':checkObj.preview,}, context, check=False)
                if  committed:
                    self.wf_message_post(cr, uid, [objDoc.id], body=_('Document restored from backup.'))
                else:
                    logging.warning("action_restore_document : Unable to restore the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+") from backup set.")
                    raise osv.except_osv(_('Check-In Error'), _("Unable to restore the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+") from backup set.\n Check if it's checked-in, before to proceed."))
        self.unlink(cr, uid, ids, context)
        return committed

plm_backupdoc()

