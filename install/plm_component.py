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
import os
import time
import types
from tools.translate import _
from osv import osv, fields
from datetime import datetime
import logging

#USED_STATES=[('draft','Draft'),('confirmed','Confirmed'),('released','Released'),('undermodify','UnderModify'),('obsoleted','Obsoleted')]
#STATEFORRELEASE=['confirmed']
#STATESRELEASABLE=['confirmed','transmitted','released','undermodify','obsoleted']

class plm_component(osv.osv):
    _inherit = 'product.product'
    _columns = {
                'create_date': fields.datetime('Date Created', readonly=True),
                'write_date': fields.datetime('Date Modified', readonly=True),
    }

#   Internal methods
    def _extract_data(self,cr,uid,ids,allIDs, anag_fields=False, rel_fields=False):
        """
            action to be executed for Transmitted state.
            Transmit the object to ERP Metodo
        """
        if not anag_fields:
            anag_fields=['name','description']
        if not rel_fields:
            rel_fields=['bom_id','product_id','product_qty','itemnum']
        outputpath=r'C:\Temp'
        if not os.path.exists(outputpath):
            raise osv.except_osv(_('Export Data Error'), _("Requested writing path (%s) doesn't exist." %(outputpath)))
            return False 
        fname=datetime.now().isoformat(' ').replace('.','').replace(':','').replace(' ','').replace('-','')+'.csv'
        filename=os.path.join(outputpath,fname)
        expData=self.export_data(cr, uid, allIDs,anag_fields)
        if not self._export_csv(filename, anag_fields, expData, True):
            raise osv.except_osv(_('Export Data Error'), _("Writing operations on file (%s) have failed." %(filename)))
            return False
        bomType=self.pool.get('mrp.bom')
        for id in ids:
            component=self.browse(cr, uid, id)
            fname=str(component.name)+'.csv'
            filename=os.path.join(outputpath,fname)
            relIDs=self._getExplodedBom(cr, uid, [id], 1, 0)
            if len(relIDs)>0:
                expData=bomType.export_data(cr, uid, relIDs,rel_fields)
                if not self._export_csv(filename, rel_fields, expData, True):
                    raise osv.except_osv(_('Export Data Error'), _("No Bom extraction files was generated, about entity (%s)." %(fname)))
                    return False
        return True

    def _export_csv(self, fname, fields, result, write_title=False):
        import csv
        if not 'datas' in result:
            logging.error("_export_csv : No 'datas' in result.")
            return False
        try:
            fp = file(fname, 'wb+')
            writer = csv.writer(fp)
            if write_title:
                writer.writerow(fields)
            results=result['datas']
            for datas in results:
                row = []
                for data in datas:
                    if type(data)==types.StringType:
                        row.append(data.replace('\n',' ').replace('\t',' '))
                    else:
                        row.append(data or '')
                writer.writerow(row)
            fp.close()
            return True
        except IOError, (errno, strerror):
            logging.error("_export_csv : IOError : ("+str(strerror)+").")
            return False
           
    def _getbyrevision(self, cr, uid, name, revision):
        result=None
        results=self.search(cr,uid,[('engineering_code','=',name),('engineering_revision','=',revision)])
        for result in results:
            break
        return result

    def _getExplodedBom(self, cr, uid, ids, level=0, currlevel=0):
        """
            Return a flat list of all children in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        result=[]
        if level==0 and currlevel>1:
            return result
        components=self.pool.get('product.product').browse(cr, uid, ids)
        relType=self.pool.get('mrp.bom')
        for component in components: 
            for bomid in component.bom_ids:
                children=relType.GetExplodedBom(cr, uid, [bomid.id], level, currlevel)
                result.extend(children)
        return result

    def _getChildrenBom(self, cr, uid, component, level=0, currlevel=0, context=None):
        """
            Return a flat list of each child, listed once, in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        result=[]
        buffer=[]
        if level==0 and currlevel>1:
            return buffer
        for bomid in component.bom_ids:
            for bom in bomid.bom_lines:
                children=self._getChildrenBom(cr, uid, bom.product_id, level, currlevel+1, context=context)
                buffer.extend(children)
        if not (component.id in buffer):
            buffer.append(component.id)
        for id in buffer:
            result.append(id)
        return result

    def getLastTime(self, cr, uid, id, default=None, context=None):
        obj = self.browse(cr, uid, id, context=context)
        return self.getUpdTime(obj)

    def getUpdTime(self, obj):
        if(obj.write_date!=False):
            return datetime.strptime(obj.write_date,'%Y-%m-%d %H:%M:%S')
        else:
            return datetime.strptime(obj.create_date,'%Y-%m-%d %H:%M:%S')

##  Customized Automations
    def on_change_name(self, cr, uid, id, name=False, engineering_code=False):
        if name:
            existingIDs=self.search(cr, uid, [('name','=',name)])
            if existingIDs:
#                raise osv.except_osv(_('Manual Numbering Warning'), _("Part number already exists."))
                return {'value': {'name': ''}}
            if not engineering_code:
                return {'value': {'engineering_code': name}}            
        return {}

##  External methods
    def Clone(self, cr, uid, id, default=None, context=None):
        """
            create a new revision of the component
        """
        newID=None
        defaults={}
        exitValues={}
        newID=self.copy(cr,uid,id,defaults,context)
        if newID != None:
            newEnt=self.browse(cr,uid,newID,context=context)
            exitValues['_id']=newID
            exitValues['name']=newEnt.name
            exitValues['engineering_code']=newEnt.engineering_code
            exitValues['engineering_revision']=newEnt.engineering_revision
        return exitValues

    def newVersion(self,cr,uid,ids,context=None):
        """
            create a new version of the document (to WorkFlow calling)
        """
        if self.newRevision(cr,uid,ids,context=context)!=None:
            return True 
        return False 

    def NewRevision(self,cr,uid,ids,context=None):
        """
            create a new revision of current component
        """
        newID=None
        newIndex=0
        oldObjects=self.browse(cr, uid, ids, context=context)
        for oldObject in oldObjects:
            newIndex=int(oldObject.engineering_revision)+1
            defaults={}
            defaults['engineering_writable']=False
            defaults['state']='undermodify'
            self.write(cr, uid, [oldObject.id], defaults, context=context, check=False)
            # store updated infos in "revision" object
            defaults['name']=oldObject.name                 # copy function needs an explicit name value
            defaults['engineering_revision']=newIndex
            defaults['engineering_writable']=True
            defaults['state']='draft'
            defaults['linkeddocuments']=[]                  # Clean attached documents for new revision object
            newID=self.copy(cr, uid, oldObject.id, defaults, context=context)
            # create a new "old revision" object
            break
        return (newID, newIndex) 

    def SaveOrUpdate(self, cr, uid, ids, default=None, context=None):
        """
            Save or Update Parts
        """
        listedParts=[]
        retValues=[]
        for part in ids:
            hasSaved=False
            if part['engineering_code'] in listedParts:
                continue
            if not ('engineering_code' in part) or (not 'engineering_revision' in part):
                part['componentID']=False
                part['hasSaved']=hasSaved
                continue
            existingID=self.search(cr,uid,[
                                           ('engineering_code','=',part['engineering_code'])
                                          ,('engineering_revision','=',part['engineering_revision'])])
            if not existingID:
                existingID=self.create(cr,uid,part)
                hasSaved=True
            else:
                existingID=existingID[0]
                objPart=self.browse(cr, uid, existingID)
                if (self.getUpdTime(objPart)<datetime.strptime(part['lastupdate'],'%Y-%m-%d %H:%M:%S')):
                    if objPart.engineering_writable:
                        del(part['lastupdate'])
                        if not self.write(cr,uid,[existingID], part , context=context, check=True):
                            raise osv.except_osv(_('Update Part Error'), _("Part %s cannot be updated" %(str(part['engineering_code']))))
                        hasSaved=True
                part['name']=objPart.name
            part['componentID']=existingID
            part['hasSaved']=hasSaved
            retValues.append(part)
            listedParts.append(part['engineering_code'])
        return retValues 

##  Work Flow Internal Methods
    def _get_recursive_parts(self, cr, uid, ids, excludeStatuses, includeStatuses):
        """
            release the object recursively
        """
        stopFlag=False
        tobeReleasedIDs=[]
        children=[]
        components=self.browse(cr, uid, ids)
        for component in components:
            children=self._getChildrenBom(cr, uid, component, 1)
            children=self.browse(cr, uid, children)
            for child in children:
                if (not child.state in excludeStatuses) and (not child.state in includeStatuses):
                    stopFlag=True
                    break
                if child.state in includeStatuses:
                    if not child.id in tobeReleasedIDs:
                        tobeReleasedIDs.append(child.id)
        return (stopFlag,tobeReleasedIDs)
    
    def _action_ondocuments(self,cr,uid,ids,action_name,context=None):
        """
            move workflow on documents having the same state of component 
        """
        docIDs=[]
        documentType=self.pool.get('ir.attachment')
        oldObjects=self.browse(cr, uid, ids, context=context)
            
        for oldObject in oldObjects:
            if (action_name!='transmit') and (action_name!='reject') and (action_name!='release'):
                check_state=oldObject.state
            else:
                check_state='confirmed'
            for document in oldObject.linkeddocuments:
                if document.state == check_state:
                    if not document.id in docIDs:
                        docIDs.append(document.id)
        if len(docIDs)>0:
            if action_name=='confirm':
                documentType.action_confirm(cr,uid,docIDs)
            elif action_name=='transmit':
                documentType.action_confirm(cr,uid,docIDs)
            elif action_name=='draft':
                documentType.action_draft(cr,uid,docIDs)
            elif action_name=='correct':
                documentType.action_draft(cr,uid,docIDs)
            elif action_name=='reject':
                documentType.action_draft(cr,uid,docIDs)
            elif action_name=='release':
                documentType.action_release(cr,uid,docIDs)
            elif action_name=='undermodify':
                documentType.action_cancel(cr,uid,docIDs)
            elif action_name=='suspend':
                documentType.action_suspend(cr,uid,docIDs)
            elif action_name=='reactivate':
                documentType.action_reactivate(cr,uid,docIDs)
            elif action_name=='obsolete':
                documentType.action_obsolete(cr,uid,docIDs)
        return docIDs

##  Work Flow Actions
    def action_draft(self,cr,uid,ids,context=None):
        """
            release the object
        """
        defaults={}
        defaults['engineering_writable']=True
        defaults['state']='draft'
        excludeStatuses=['draft','released','undermodify','obsoleted']
        includeStatuses=['confirmed','transmitted']
        stopFlag,allIDs=self._get_recursive_parts(cr, uid, ids, excludeStatuses, includeStatuses)
        self._action_ondocuments(cr,uid,allIDs,'draft')
        return self.write(cr, uid, allIDs, defaults, context=context, check=False)

    def action_confirm(self,cr,uid,ids,context=None):
        """
            action to be executed for Draft state
        """
        defaults={}
        defaults['engineering_writable']=False
        defaults['state']='confirmed'
        excludeStatuses=['confirmed','transmitted','released','undermodify','obsoleted']
        includeStatuses=['draft']
        stopFlag,allIDs=self._get_recursive_parts(cr, uid, ids, excludeStatuses, includeStatuses)
        self._action_ondocuments(cr,uid,allIDs,'confirm')
        return self.write(cr, uid, allIDs, defaults, context=context, check=False)

    def action_release(self,cr,uid,ids,context=None):
        """
           action to be executed for Released state
        """
        defaults={}
        excludeStatuses=['released','undermodify','obsoleted']
        includeStatuses=['confirmed']
        stopFlag,allIDs=self._get_recursive_parts(cr, uid, ids, excludeStatuses, includeStatuses)
        if len(allIDs)<1 or stopFlag:
            raise osv.except_osv(_('WorkFlow Error'), _("Part cannot be released."))
        oldObjects=self.browse(cr, uid, allIDs, context=context)
        for oldObject in oldObjects:
            last_id=self._getbyrevision(cr, uid, oldObject.engineering_code, oldObject.engineering_revision-1)
            if last_id != None:
                defaults['engineering_writable']=False
                defaults['state']='obsoleted'
                self.write(cr,uid,[last_id],defaults ,context=context,check=False)
            defaults['engineering_writable']=False
            defaults['state']='released'
        self._action_ondocuments(cr,uid,allIDs,'release')
        return self.write(cr,uid,allIDs,defaults ,context=context,check=False)

    def action_obsolete(self,cr,uid,ids,context=None):
        """
            obsolete the object
        """
        defaults={}
        defaults['engineering_writable']=True
        defaults['state']='obsoleted'
        excludeStatuses=['draft','confirmed','transmitted','undermodify','obsoleted']
        includeStatuses=['released']
        stopFlag,allIDs=self._get_recursive_parts(cr, uid, ids, excludeStatuses, includeStatuses)
        self._action_ondocuments(cr,uid,allIDs,'obsolete')
        return self.write(cr, uid, allIDs, defaults, context=context, check=False)

    def action_reactivate(self,cr,uid,ids,context=None):
        """
            reactivate the object
        """
        defaults={}
        defaults['engineering_writable']=True
        defaults['state']='released'
        excludeStatuses=['draft','confirmed','transmitted','released','undermodify','obsoleted']
        includeStatuses=['obsoleted']
        stopFlag,allIDs=self._get_recursive_parts(cr, uid, ids, excludeStatuses, includeStatuses)
        self._action_ondocuments(cr,uid,allIDs,'reactivate')
        return self.write(cr, uid, allIDs, defaults, context=context, check=False)

#   Overridden methods for this entity
    def create(self, cr, user, vals, context=None):
        existingIDs=self.search(cr, user, [('name','=',vals['name'])], order = 'engineering_revision', context=context)
        if 'engineering_code' in vals:
            if vals['engineering_code'] == False:
                vals['engineering_code'] = vals['name']
        else:
            vals['engineering_code'] = vals['name']
        if len(existingIDs)>0:
            return existingIDs[len(existingIDs)-1]           #TODO : Manage search for highest revisonid
        else:
            try:
                return super(plm_component,self).create(cr, user, vals, context=context)
            except:
                raise Exception(_("It has tried to create %s , %s"%(str(vals['name']),str(vals))))
                return False
         
    def write(self, cr, user, ids, vals, context=None, check=True):
        checkState=('confirmed','released','undermodify','obsoleted')
        if check:
            customObjects=self.browse(cr, user, ids, context=context)
            for customObject in customObjects:
                if not customObject.engineering_writable:
                    raise osv.except_osv(_('Edit Entity Error'), _("No changes are allowed on entity (%s)." %(customObject.name)))
                    return False
                if customObject.state in checkState:
                    raise osv.except_osv(_('Edit Entity Error'), _("The active state does not allow you to make save action"))
                    return False
                if customObject.engineering_code == False:
                    vals['engineering_code'] = customObject.name
                    # Force copy engineering_code to name if void
        return super(plm_component,self).write(cr, user, ids, vals, context=context)  

    def copy(self,cr,uid,id,defaults={},context=None):
        """
            Overwrite the default copy method
        """
        previous_name=self.browse(cr,uid,id,context=context).name
        if not 'name' in defaults:
            new_name='Copy of %s'%previous_name
            l=self.search(cr,uid,[('name','like',new_name)],context=context)
            if len(l)>0:
                new_name='%s (%s)'%(new_name,len(l)+1)
            defaults['name']=new_name
            defaults['engineering_code']=new_name
            defaults['engineering_revision']=0
        #assign default value
        defaults['state']='draft'
        defaults['engineering_writable']=True
        defaults['write_date']=None
        defaults['linkeddocuments']=[]
        return super(plm_component,self).copy(cr,uid,id,defaults,context=context)
#   Overridden methods for this entity

plm_component()
