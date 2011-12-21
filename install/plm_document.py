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
import tools
import os
import logging

from tools.translate import _
from osv import osv, fields
from osv.orm import except_orm
import time
from datetime import datetime

# To be adequated to plm.component class states
USED_STATES=[('draft','Draft'),('confirmed','Confirmed'),('released','Released'),('undermodify','UnderModify'),('obsoleted','Obsoleted')]
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
    _name = 'ir.attachment'
    _inherit = 'ir.attachment'

    def _is_checkedout_for_me(self, cr, uid, id, context=None):
        """
            Get if given document (or its latest revision) is checked-out for the requesting user
        """
        act=False
        lastDoc=self._getlastrev(cr, uid, [id], context)
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
        treated = []
        objects = self.browse(cr, uid, ids, context=context)
        for object in objects:
            if object in treated:
                continue
            docIds=self.search(cr,uid,[('name','=',object.name)],order='revisionid',context=context)
            result.append(docIds[len(docIds)-1])
            treated.append(object)
        return result
            
    def _data_get_files(self, cr, uid, ids, listedFiles=([],[]), forceFlag=False, context=None):
        """
            Get Files to return to Client
        """
        result = []
        datefiles,listfiles=listedFiles
        objects = self.browse(cr, uid, ids, context=context)
        for object in objects:
            try:
                isCheckedOutToMe=self._is_checkedout_for_me(cr, uid, object.id, context)
                if not(object.datas_fname in listfiles):
                    value = file(os.path.join(self._get_filestore(cr), object.store_fname), 'rb').read()
                    result.append((object.id, object.datas_fname, base64.encodestring(value), isCheckedOutToMe))
                else:
                    if forceFlag:
                        isNewer=True
                    else:
                        isNewer=self.getLastTime(cr,uid,object.id)>=datetime.strptime(str(datefiles[listfiles.index(object.datas_fname)]),'%Y-%m-%d %H:%M:%S')
                    if (isNewer and not(isCheckedOutToMe)):
                        value = file(os.path.join(self._get_filestore(cr), object.store_fname), 'rb').read()
                        result.append((object.id, object.datas_fname, base64.encodestring(value), isCheckedOutToMe))
                    else:
                        result.append((object.id,object.datas_fname,None, isCheckedOutToMe))
            except Exception, ex:
                logging.error("_data_get_files : Unable to access to document ("+str(object.name)+"). Error :" + str(ex))
                result.append((object.id,object.datas_fname,None, True))
        return result
            
    def _data_get(self, cr, uid, ids, name, arg, context):
        result = {}
        objects = self.browse(cr, uid, ids, context=context)
        for object in objects:
            if not object.store_fname:
                raise osv.except_osv(_('Stored Document Error'), _("Document %s - %s cannot be accessed" %(str(object.name),str(object.revisionid))))
            filestore=os.path.join(self._get_filestore(cr), object.store_fname)
            if os.path.exists(filestore):
                value = file(filestore, 'rb').read()
                if len(value)>0:
                    result[object.id] = base64.encodestring(value)
                else:
                    result[object.id] = ''
            else:
                result[object.id] = ''
        return result

    def _data_set(self, cr, uid, id, name, value, args=None, context=None):
        if not value:
            filename = self.browse(cr, uid, id, context).store_fname
            try:
                os.unlink(os.path.join(self._get_filestore(cr), filename))
            except:
                pass
            cr.execute('update ir_attachment set store_fname=NULL WHERE id=%s', (id,) )
            return True
        #if (not context) or context.get('store_method','fs')=='fs':
        try:
            fname,filesize=self._manageFile(cr,uid,id,binvalue=value,context=context)
            cr.execute('update ir_attachment set store_fname=%s,file_size=%s where id=%s', (fname,filesize,id))
            return True
        except Exception,e :
            raise except_orm(_('Error in _data_set'), str(e))

    def _explodedocs(self, cr, uid, id, kind, listed_documents=[], recursion=True):
        result=[]
        if (id in listed_documents):
            return result
        documentRelation=self.pool.get('plm.document.relation')
        docRelIds=documentRelation.search(cr,uid,[('parent_id', '=',id),('link_kind', '=',kind)])
        if len(docRelIds)==0:
            return result
        children=documentRelation.browse(cr,uid,docRelIds)
        for child in children:
            if recursion:
                listed_documents.append(id)
                result.extend(self._explodedocs(cr, uid, child.child_id.id, kind, listed_documents,recursion))
            result.append(child.child_id.id)
        return result

    def _relateddocs(self, cr, uid, id, kind, listed_documents=[], recursion=True):
        result=[]
        if (id in listed_documents):
            return result
        documentRelation=self.pool.get('plm.document.relation')
        docRelIds=documentRelation.search(cr,uid,[('child_id', '=',id),('link_kind', '=',kind)])
        if len(docRelIds)==0:
            return result
        children=documentRelation.browse(cr,uid,docRelIds)
        for child in children:
            if recursion:
                listed_documents.append(id)
                result.extend(self._relateddocs(cr, uid, child.parent_id.id, kind, listed_documents, recursion))
            if child.parent_id.id:
                result.append(child.parent_id.id)
        return result

    def _relatedbydocs(self, cr, uid, id, kind, listed_documents=[], recursion=True):
        result=[]
        if (id in listed_documents):
            return result
        documentRelation=self.pool.get('plm.document.relation')
        docRelIds=documentRelation.search(cr,uid,[('parent_id', '=',id),('link_kind', '=',kind)])
        if len(docRelIds)==0:
            return result
        children=documentRelation.browse(cr,uid,docRelIds)
        for child in children:
            if recursion:
                listed_documents.append(id)
                result.extend(self._relatedbydocs(cr, uid, child.child_id.id, kind, listed_documents, recursion))
            if child.child_id.id:
                result.append(child.child_id.id)
        return result

    def _data_check_files(self, cr, uid, ids, listedFiles=(), forceFlag=False, context=None):
        result = []
        datefiles,listfiles=listedFiles
        objects = self.browse(cr, uid, ids, context=context)
        for object in objects:
            isCheckedOutToMe=self._is_checkedout_for_me(cr, uid, object.id, context)
            if (object.datas_fname in listfiles):
                if forceFlag:
                    isNewer = True
                else:
                    isNewer=self.getLastTime(cr,uid,object.id)>=datetime.strptime(str(datefiles[listfiles.index(object.datas_fname)]),'%Y-%m-%d %H:%M:%S')
                collectable = isNewer and not(isCheckedOutToMe)
            else:
                collectable = True
            result.append((object.id, object.datas_fname, object.file_size, collectable, isCheckedOutToMe))
        return result
            
    def copy(self,cr,uid,id,defaults={},context=None):
        """
            Overwrite the default copy method
        """
        #get All document relation 
        documentRelation=self.pool.get('plm.document.relation')
        docRelIds=documentRelation.search(cr,uid,[('parent_id', '=',id)],context=context)
        if len(docRelIds)==0:
            docRelIds=False 
        previous_name=self.browse(cr,uid,id,context=context).name
        if not 'name' in defaults:
            new_name='Copy of %s'%previous_name
            l=self.search(cr,uid,[('name','=',new_name)],order='revisionid',context=context)
            if len(l)>0:
                new_name='%s (%s)'%(new_name,len(l)+1)
            defaults['name']=new_name
        #manage copy of the file
        fname,filesize=self._manageFile(cr,uid,id,context=context)
        #assign default value
        defaults['store_fname']=fname
        defaults['file_size']=filesize
        defaults['state']='draft'
        defaults['writable']=True
        newID=super(plm_document,self).copy(cr,uid,id,defaults,context=context)
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

    def _manageFile(self,cr,uid, id, binvalue=None, context=None):
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
            fileStream=self._data_get(cr, uid, [id], name=None, arg=None, context=context)
            binvalue=fileStream[fileStream.keys()[0]]
        
        flag = flag or create_directory(path)
        filename = random_name()
        fname = os.path.join(path, flag, filename)
        fobj = file(fname,'wb')
        value = base64.decodestring(binvalue)
        fobj.write(value)
        fobj.close()
        return (os.path.join(flag,filename),len(value))
    
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
        oldObjects=self.browse(cr,uid,ids,context=context)
        for oldObject in oldObjects:
            self.write(cr,uid,[oldObject.id],{'state':'undermodify',} ,context=context,check=False)
            defaults={}
            defaults['name']=oldObject.name
            defaults['revisionid']=int(oldObject.revisionid)+1
            defaults['writable']=True
            defaults['state']='draft'
            newID=super(plm_document,self).copy(cr,uid,oldObject.id,defaults,context=context)
            break
        return (newID, defaults['revisionid']) 
    
    def Clone(self, cr, uid, id, defaults={}, context=None):
        """
            create a new revision of the document
        """
        defaults={}
        exitValues={}
        newID=self.copy(cr,uid,id,defaults,context)
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
                objDocument=self.browse(cr, uid, existingID)
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
                objDocument=self.browse(cr, uid, existingID)
#                logging.info("SaveOrUpdate : time db : %s time file : %s" %(str(self.getLastTime(cr,uid,existingID).strftime('%Y-%m-%d %H:%M:%S')), str(document['lastupdate'])))
                if self.getLastTime(cr,uid,existingID)<datetime.strptime(str(document['lastupdate']),'%Y-%m-%d %H:%M:%S'):
                    if objDocument.writable:
                        del(document['lastupdate'])
                        if not self.write(cr,uid,[existingID], document , context=context, check=True):
                            raise osv.except_osv(_('Update Document Error'), _("Document %s - %s cannot be updated" %(str(document['name']), str(document['revisionid']))))
                        hasSaved=True
            document['documentID']=existingID
            document['hasSaved']=hasSaved
            document['hasUpdated']=hasUpdated
            retValues.append(document)
        return retValues 

    def UpdateDocuments(self, cr, uid, documents, default=None, context=None):
        """
            Save or Update Documents
        """
        ret=True
        for document in documents:
            id=document['documentID']
            del(document['documentID'])
            ret=ret and self.write(cr,uid,[id], document , context=context, check=True)
        return ret 

    def CleanUp(self, cr, uid, ids, default=None, context=None):
        """
            Remove faked documents
        """
        cr.execute('delete from ir_attachment where store_fname=NULL')
        return True 

    def _check_in(self, cr, uid, ids, context=None):
        """
            move workflow on documents having the same state of component 
        """
        documents=self.browse(cr, uid, ids, context=context)
        checkoutType=self.pool.get('plm.checkout')
             
        for document in documents:
            if checkoutType.search(cr, uid, [('documentid','=',document.id)], context=context):
                raise osv.except_osv(_('WorkFlow Error'), _("The document %s - %s has not checked-in" %(str(document.name),str(document.revisionid))))
        return False
 
    def action_draft(self, cr, uid, ids, *args):
        """
            release the object
        """
        defaults={}
        defaults['writable']=True
        defaults['state']='draft'
        return self.write(cr, uid, ids, defaults, check=False)

    def action_confirm(self,cr,uid,ids,context=None):
        """
            action to be executed for Draft state
        """
        defaults={}
        defaults['writable']=False
        defaults['state']='confirmed'
        self._check_in(cr, uid, ids,context)
        return self.write(cr, uid, ids, defaults, context=context, check=False)

    def action_release(self, cr, uid, ids, *args):
        """
            release the object
        """
        defaults={}
        oldObjects=self.browse(cr, uid, ids)
        for oldObject in oldObjects:
            last_id=self._getbyrevision(cr, uid, oldObject.name, oldObject.revisionid-1)
            if last_id != None:
                defaults['writable']=False
                defaults['state']='obsoleted'
                self.write(cr, uid, [last_id], defaults, check=False)
        defaults['writable']=False
        defaults['state']='released'
        self._check_in(cr, uid, ids)
        return self.write(cr, uid, ids, defaults, check=False)

    def action_obsolete(self,cr,uid,ids,context=None):
        """
            obsolete the object
        """
        defaults={}
        defaults['writable']=False
        defaults['state']='obsoleted'
        self._check_in(cr, uid, ids,context)
        return self.write(cr, uid, ids, defaults, context=context, check=False)

    def action_reactivate(self,cr,uid,ids,context=None):
        """
            reactivate the object
        """
        defaults={}
        defaults['engineering_writable']=False
        defaults['state']='released'
        self._check_in(cr, uid, ids,context)
        return self.write(cr, uid, ids, defaults, context=context, check=False)

#   Overridden methods for this entity
    def write(self, cr, user, ids, vals, context=None, check=True):
        checkState=('confirmed','released','undermodify','obsoleted')
        if check:
            customObjects=self.browse(cr,user,ids,context=context)
            for customObject in customObjects:
                if customObject.state in checkState:
                    raise osv.except_osv(_('Edit Entity Error'), _("The active state does not allow you to make save action"))
                    return False
        return super(plm_document,self).write(cr, user, ids, vals, context=context)

    def _check_duplication(self, cr, uid, vals, ids=[], op='create'):
        """
            Overridden, due to revision id management, filename can be duplicated, 
            because system has to manage several revisions of a document.
        """
        name = vals.get('name', False)
        parent_id = vals.get('parent_id', False)
        res_model = vals.get('res_model', False)
        res_id = vals.get('res_id', 0)
        revisionid = vals.get('revisionid', 0)
        if op == 'write':
            for file in self.browse(cr, uid, ids): # FIXME fields_only
                if not name:
                    name = file.name
                if not parent_id:
                    parent_id = file.parent_id and file.parent_id.id or False
                if not res_model:
                    res_model = file.res_model and file.res_model or False
                if not res_id:
                    res_id = file.res_id and file.res_id or 0
                if not revisionid:
                    revisionid = file.revisionid and file.revisionid or 0
                res = self.search(cr, uid, [('id', '<>', file.id), ('name', '=', name), ('parent_id', '=', parent_id), ('res_model', '=', res_model), ('res_id', '=', res_id), ('revisionid', '=', revisionid)])
                if len(res)>1:
                    return False
        if op == 'create':
            res = self.search(cr, uid, [('name', '=', name), ('parent_id', '=', parent_id), ('res_id', '=', res_id), ('res_model', '=', res_model), ('revisionid', '=', revisionid)])
            if len(res):
                return False
        return True
         
    _columns = {
                'revisionid': fields.integer('Revision Index', required=True),
                'writable': fields.boolean('Writable'),
                'datas': fields.function(_data_get,method=True,fnct_inv=_data_set,string='File Content',type="binary"),
                'printout': fields.binary('Printout Content'),
                'preview': fields.binary('Preview Content'),
                'state':fields.selection(USED_STATES,'Status',readonly="True",required=True),
    }    

    _defaults = {
                 'revisionid': lambda *a: 0,
                 'writable': lambda *a: True,
                 'state': lambda *a: 'draft',
    }

    _sql_constraints = [
        ('filename_uniq', 'unique (name,partner_id,res_id,res_model,revisionid)', 'File name has to be unique!') # qui abbiamo la sicurezza dell'univocita del nome file
    ]

    def CheckedIn(self, cr, uid, files, default=None, context=None):
        retValues=[]
        def getcheckedfiles(files):
            res=[]
            for file in files:
                ids=self.search(cr,uid,[('datas_fname','=',file)],order='revisionid')
                if len(ids)>0:
                    res.append([file,not(self._is_checkedout_for_me(cr, uid, ids[0], context))])
            return res
        
        if len(files)>0: # no files to process 
            retValues=getcheckedfiles(files)
        return retValues


    def CheckAllFiles(self, cr, uid, request, default=None, context=None):
        """
            Evaluate documents to return
        """
        forceFlag=False
        listed_models=[]
        listed_documents=[]
        id, listedFiles, selection = request        
        if selection == None:
            selection=1
        if selection<0:
            forceFlag=True
            selection=selection*(-1)

        kind='LyTree'   # Get relations due to layout connected
        docArray=self._relateddocs(cr, uid, id, kind, listed_documents)

        kind='HiTree'   # Get Hierarchical tree relations due to children
        modArray=self._explodedocs(cr, uid, id, kind, listed_models)
        for item in docArray:
            if item not in modArray:
                modArray.append(item)
        docArray=modArray  
        if selection == 2:
            docArray=self._getlastrev(cr, uid, docArray, context)
        
        if not id in docArray:
            docArray.append(id)     # Add requested document to package
        return self._data_check_files(cr, uid, docArray, listedFiles, forceFlag, context)

    def GetSomeFiles(self, cr, uid, request, default=None, context=None):
        """
            Extract documents to be returned 
        """
        forceFlag=False
        ids, listedFiles, selection = request
        if selection == None:
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
        id, listedFiles, selection = request
        if selection == None:
            selection=1

        if selection<0:
            forceFlag=True
            selection=selection*(-1)

        kind='LyTree'   # Get relations due to layout connected
        docArray=self._relateddocs(cr, uid, id, kind, listed_documents)

        kind='HiTree'   # Get Hierarchical tree relations due to children
        modArray=self._explodedocs(cr, uid, id, kind, listed_models)
        for item in docArray:
            if item not in modArray:
                modArray.append(item)
        docArray=modArray  
        if selection == 2:
            docArray=self._getlastrev(cr, uid, docArray, context)
        
        if not id in docArray:
            docArray.append(id)     # Add requested document to package
        return self._data_get_files(cr, uid, docArray, listedFiles, forceFlag, context)

    def GetRelatedDocs(self, cr, uid, ids, default=None, context=None):
        """
            Extract documents related to current one(s) (layouts, referred models, etc.)
        """
        related_documents=[]
        listed_documents=[]
        read_docs=[]
        for id in ids:
            kind='RfTree'   # Get relations due to referred models
            read_docs.extend(self._relateddocs(cr, uid, id, kind, listed_documents, False))
            read_docs.extend(self._relatedbydocs(cr, uid, id, kind, listed_documents, False))

            kind='LyTree'   # Get relations due to layout connected
            read_docs.extend(self._relateddocs(cr, uid, id, kind, listed_documents, False))
            read_docs.extend(self._relatedbydocs(cr, uid, id, kind, listed_documents, False))
       
        documents=self.browse(cr, uid, read_docs, context=context)
        for document in documents:
            related_documents.append([document.id,document.name,document.preview])
        return related_documents

    def getServerTime(self, cr, uid, id, default=None, context=None):
        """
            calculate the server db time 
        """
        return datetime.now()
    
    def getLastTime(self, cr, uid, id, default=None, context=None):
        """
            get document last modification time 
        """
        obj = self.browse(cr, uid, id, context=context)
        if(obj.write_date!=False):
            return datetime.strptime(obj.write_date,'%Y-%m-%d %H:%M:%S')
        else:
            return datetime.strptime(obj.create_date,'%Y-%m-%d %H:%M:%S')

    def getUserSign(self, cr, uid, id, default=None, context=None):
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
    
    def getCheckedOut(self, cr, uid, id, default=None, context=None):
        checkoutType=self.pool.get('plm.checkout')
        checkoutIDs=checkoutType.search(cr,uid,[('documentid', '=',id)])
        for checkoutID in checkoutIDs:
            object=checkoutType.browse(cr,uid,checkoutID)
            return(object.documentid.name,object.documentid.revisionid,self.getUserSign(cr,object.userid.id,1),object.hostname)
        return False

plm_document()


class plm_checkout(osv.osv):
    _name = 'plm.checkout'
    _columns = {
                'userid':fields.many2one('res.users', 'Related User', ondelete='cascade'), 
                'hostname':fields.char('hostname',size=64), 
                'hostpws':fields.char('PWS Directory',size=1024), 
                'documentid':fields.many2one('ir.attachment', 'Related Document', ondelete='cascade'), 
                'createdate':fields.datetime('Date Created', readonly=True)
    }
    _defaults = {
        'createdate': lambda self,cr,uid,ctx:time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _sql_constraints = [
        ('documentid', 'unique (documentid)', 'The documentid must be unique !') 
    ]

    def create(self, cr, uid, vals, context=None):
        if context!=None and context!={}:
            return False
        documentType=self.pool.get('ir.attachment')
        docID=documentType.browse(cr, uid, vals['documentid'])
        values={'writable':True,}
        if not documentType.write(cr, uid, [docID.id], values):
            logging.warning("create : Unable to check-out the required document ("+str(docID.name)+"-"+str(docID.revisionid)+").")
            raise osv.except_osv(_('Check-Out Error'), _("Unable to check-out the required document ("+str(docID.name)+"-"+str(docID.revisionid)+")."))
            return False
        return super(plm_checkout,self).create(cr, uid, vals, context=context)   
         
    def unlink(self, cr, uid, ids, context=None):
        if context!=None and context!={}:
            if uid!=1:
                logging.warning("unlink : Unable to Check-In the required document.\n You aren't authorized in this context.")
                raise osv.except_osv(_('Check-In Error'), _("Unable to Check-In the required document.\n You aren't authorized in this context."))
                return False
        documentType=self.pool.get('ir.attachment')
        checkObjs=self.browse(cr, uid, ids)
        for checkObj in checkObjs:
            checkObj.documentid.writable=False
            values={'writable':False,}
            if not documentType.write(cr, uid, [checkObj.documentid.id], values):
                logging.warning("unlink : Unable to check-in the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+").\n You can't change writable flag.")
                raise osv.except_osv(_('Check-In Error'), _("Unable to Check-In the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+").\n You can't change writable flag."))
                return False
        return super(plm_checkout,self).unlink(cr, uid, ids, context=context)

plm_checkout()


class plm_document_relation(osv.osv):
    _name = 'plm.document.relation'
    _columns = {'parent_id':fields.many2one('ir.attachment', 'Related parent document', ondelete='cascade'), 
                'child_id':fields.many2one('ir.attachment', 'Related child document',  ondelete='cascade'),
                'configuration':fields.char('Filename',size=1024),
                'link_kind': fields.char('Kind of Link',size=64, required=True)
               }
    _defaults = {
                 'link_kind': lambda *a: 'HiTree'
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
            for relation in relations:
                res['parent_id'],res['child_id'],res['configuration'],res['link_kind']=relation
                if (res['link_kind']=='LyTree') or (res['link_kind']=='RfTree'):
                    to_remove=res['child_id']
                    criteria='child_id'
                else:
                    to_remove=res['parent_id']
                    criteria='parent_id'
                ids=self.search(cr,uid,[(criteria,'=',to_remove),('link_kind','=',res['link_kind'])])
                self.unlink(cr,uid,ids)

        def saveChild(args):
            """
                save the relation 
            """
            try:
                res={}
                res['parent_id'],res['child_id'],res['configuration'],res['link_kind']=args
                if (res['parent_id']!= None) and (res['child_id']!=None):
                    if (len(str(res['parent_id']))>0) and (len(str(res['child_id']))>0):
                        if not((res['parent_id'],res['child_id']) in savedItems):
                            savedItems.append((res['parent_id'],res['child_id']))
                            self.create(cr, uid, res)
                else:
                    logging.error("saveChild : Unable to create a relation between documents. One of documents involved doesn't exist. Arguments(" + str(args) +") ")
                    raise Exception("saveChild: Unable to create a relation between documents. One of documents involved doesn't exist.")
            except:
                logging.error("saveChild : Unable to create a relation. Arguments(" + str(args) +") ")
                raise Exception("saveChild: Unable to create a relation.")
            
        savedItems=[]
        if len(relations)<1: # no relation to save 
            return False
        cleanStructure(relations)
        for relation in relations:
            saveChild(relation)
        return False

plm_document_relation()
