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

from tools.translate import _
from osv import osv, fields
from osv.orm import except_orm
import time
from datetime import datetime

# To be adequated to plm.component class states
USED_STATES=[('draft','Draft'),('confirmed','Confirmed'),('released','Released'),('undermodify','UnderModify'),('canceled','Canceled')]
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

    def _is_checkedout_for_me(self, cr, uid, id):
        act=False
        checkType=self.pool.get('plm.checkout')
        docIDs=checkType.search(cr, uid, [('documentid','=',id)])
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
            result.append(docIds[0])
            treated.append(object)
        return result
            
    def _data_get_files(self, cr, uid, ids, name, listedFiles=[], context=None):
        result = []
        objects = self.browse(cr, uid, ids, context=context)
        for object in objects:
            try:
                isCheckedOutToMe=self._is_checkedout_for_me(cr, uid, object.id)
                if not(object.datas_fname in listedFiles and isCheckedOutToMe):
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
                raise Exception(_("This document %s cannot be accessed" %(str(object.name))))
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
                logging.error("_data_set : Unable to remove document ("+str(filename)+").")
            cr.execute('update ir_attachment set store_fname=NULL WHERE id=%s', (id,) )
            return True
        try:
            filename,filesize=self._manageFile(cr,uid,id,binvalue=value,context=context)
            cr.execute('update ir_attachment set store_fname=%s,file_size=%s where id=%s', (filename,filesize,id))
            return True
        except Exception,ex :
            logging.error("_data_set : Unable to access to document ("+str(filename)+"). Error :" + str(ex))
            raise except_orm(_('Error in _data_set'), str(ex))

    def copy(self,cr,uid,id,defaults={},context=None):
        """
            Overwrite the default copy method
        """
        newID=None
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
                raise except_orm(_('Permission Denied !'), _('You have not permissions to write on the server side.'))
        
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
        newIndex=0
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
        newID=None
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
                if self.getLastTime(cr,uid,existingID)<datetime.strptime(str(document['lastupdate']),'%Y-%m-%d %H:%M:%S'):
                    if objDocument.writable:
                        del(document['lastupdate'])
                        if not self.write(cr,uid,[existingID], document , context=context, check=True):
                            raise Exception(_("This document %s cannot be updated" %(str(document['name']))))
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
                defaults['state']='canceled'
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
        return self.write(cr, uid, allIDs, defaults, context=context, check=False)

    def action_reactivate(self,cr,uid,ids,context=None):
        """
            reactivate the object
        """
        defaults={}
        defaults['engineering_writable']=False
        defaults['state']='released'
        self._check_in(cr, uid, ids,context)
        return self.write(cr, uid, allIDs, defaults, context=context, check=False)

#   Overridden methods for this entity
    def write(self, cr, user, ids, vals, context=None, check=True):
        checkState=('confirmed','released','undermodify','canceled')
        if check:
            customObjects=self.browse(cr,user,ids,context=context)
            for customObject in customObjects:
                if customObject.state in checkState:
                    logging.error(_("The workflow state of "+str(customObject.name)+" does not allow you to write its data."))
                    return False
        return super(plm_document,self).write(cr, user, ids, vals, context=context)

    def _check_in(self, cr, uid, ids, context=None):
        """
            move workflow on documents having the same state of component 
        """
        documents=self.browse(cr, uid, ids, context=context)
        checkoutType=self.pool.get('plm.checkout')
             
        for document in documents:
            if checkoutType.search(cr, uid, [('documentid','=',document.id)], context=context):
                raise Exception(_("The document %s has not checked-in" %str(document.name)))
        return False
 
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
                if len(res):
                    return False
        if op == 'create':
            res = self.search(cr, uid, [('name', '=', name), ('parent_id', '=', parent_id), ('res_id', '=', res_id), ('res_model', '=', res_model)])
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
            latest=None
            for file in files:
                ids=self.search(cr,uid,[('datas_fname','=',file)],order='revisionid')
                if len(ids)>0:
                    res.append([file,not(self._is_checkedout_for_me(cr, uid, ids[0]))])
            return res
        
        if len(files)>0: # no files to process 
            retValues=getcheckedfiles(files)
        return retValues

    def GetAllFiles(self, cr, uid, request, default=None, context=None):
        listed_models=[]
        listed_documents=[]
        def _treebom(cr, id, kind):
            result=[]
            if (id in listed_documents):
                return result
            listed_documents.append(id)
            documentRelation=self.pool.get('plm.document.relation')
            docRelIds=documentRelation.search(cr,uid,[('parent_id', '=',id),('link_kind', '=',kind)])
            if len(docRelIds)==0:
                return result
            children=documentRelation.browse(cr,uid,docRelIds,context=context)
            for child in children:
                result.extend(_treebom(cr, child.child_id.id, kind))
                result.append(child.child_id.id)
            return result

        def _laybom(cr, id, kind):
            result=[]
            if (id in listed_models):
                return result
            listed_models.append(id)
            documentRelation=self.pool.get('plm.document.relation')
            docRelIds=documentRelation.search(cr,uid,[('child_id', '=',id),('link_kind', '=',kind)])
            if len(docRelIds)==0:
                return result
            children=documentRelation.browse(cr,uid,docRelIds,context=context)
            for child in children:
                result.extend(_laybom(cr, child.parent_id.id, kind))
                result.append(child.parent_id.id)
            return result

        id, listedFiles = request
        kind='LyTree'   # Get relations due to layout connected
        docArray=_laybom(cr, id, kind)

        kind='HiTree'   # Get Hierarchical tree relations due to children
        modArray=_treebom(cr, id, kind)
        docArray=self._getlastrev(cr, uid, docArray+modArray, context)
        
        docArray.append(id)     # Add requested document to package
        exitDatas=self._data_get_files(cr, uid, docArray, '', listedFiles, context)
        return exitDatas

    def getServerTime(self, cr, uid, id, default=None, context=None):
        """
            calculate the server db time 
        """
        cr.execute("select current_timestamp;")
        return cr.fetchall()
    
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
            return False
        return super(plm_checkout,self).create(cr, uid, vals, context=context)   
         
    def unlink(self, cr, uid, ids, context=None):
        if context!=None:
            if uid!=1:
                return False
        documentType=self.pool.get('ir.attachment')
        checkObjs=self.browse(cr, uid, ids)
        for checkObj in checkObjs:
            checkObj.documentid.writable=False
            values={'writable':False,}
            if not documentType.write(cr, uid, [checkObj.documentid.id], values):
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
            latest=None
            for relation in relations:
                res['parent_id'],res['child_id'],res['configuration'],res['link_kind']=relation
                if latest==res['parent_id']:
                    continue
                latest=res['parent_id']
                ids=self.search(cr,uid,[('parent_id','=',res['parent_id']),('link_kind','=',res['link_kind'])])
                self.unlink(cr,uid,ids)

        def saveChild(args):
            """
                save the relation 
            """
            try:
                res={}
                res['parent_id'],res['child_id'],res['configuration'],res['link_kind']=args
                self.create(cr, uid, res)
            except:
                logging.error("saveChild : Unable to create a relation. Arguments(" + str(args) +") ")
                raise Exception("saveChild: Unable to create a relation.")
            
        if len(relations)<1: # no relation to save 
            return False
        cleanStructure(relations)
        for relation in relations:
            saveChild(relation)
        return False

plm_document_relation()
