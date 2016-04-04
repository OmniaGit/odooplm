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
import types
import logging
from datetime import datetime
from openerp import models, fields, api, SUPERUSER_ID, _, osv
from openerp.exceptions import ValidationError, UserError
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

USED_STATES     =   [('draft','Draft'),
                     ('confirmed','Confirmed'),
                     ('released','Released'),
                     ('undermodify','UnderModify'),
                     ('obsoleted','Obsoleted')]
USEDIC_STATES   =   dict(USED_STATES)
#STATEFORRELEASE=['confirmed']
#STATESRELEASABLE=['confirmed','transmitted','released','undermodify','obsoleted']

class plm_component(models.Model):
    _inherit = 'product.product'
    create_date     =   fields.Datetime(_('Date Created'),     readonly=True)
    write_date      =   fields.Datetime(_('Date Modified'),    readonly=True)
#   Internal methods
    def _getbyrevision(self, cr, uid, name, revision):
        result=None
        results=self.search(cr,uid,[('engineering_code','=',name),('engineering_revision','=',revision)])
        for result in results:
            break
        return result

    @api.multi
    def product_template_open(self):
        product_id = self.product_tmpl_id.id
        mod_obj = self.env['ir.model.data']
        search_res = mod_obj.get_object_reference('plm', 'product_template_form_view_plm_custom')
        form_id = search_res and search_res[1] or False
        if product_id and form_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Product Engineering'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.template',
                'res_id': product_id,
                'views': [(form_id, 'form')],
            }

    @api.multi
    def open_boms(self):
        product_tmpl_id = self.product_tmpl_id.id
        if product_tmpl_id:
            localCtx = self.env.context.copy()
            localCtx.update({'default_product_tmpl_id': product_tmpl_id, 'search_default_product_tmpl_id': product_tmpl_id})
            return {
                'type'      : 'ir.actions.act_window',
                'name'      : _('Mrp Bom'),
                'view_type' : 'form',
                'view_mode' : 'tree,form',
                'res_model' : 'mrp.bom',
                'context'   : localCtx,
            }
            
#     def _getExplodedBom(self, cr, uid, ids, level=0, currlevel=0):
#         """
#             Return a flat list of all children in a Bom ( level = 0 one level only, level = 1 all levels)
#         """
#         result=[]
#         if level==0 and currlevel>1:
#             return result
#         components=self.pool.get('product.product').browse(cr, uid, ids)
#         relType=self.pool.get('mrp.bom')
#         for component in components: 
#             for bomid in component.bom_ids:
#                 children=relType.GetExplodedBom(cr, uid, [bomid.id], level, currlevel)
#                 result.extend(children)
#         return result

    def _getChildrenBom(self, cr, uid, component, level=0, currlevel=0, context=None):
        """
            Return a flat list of each child, listed once, in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        result = []
        bufferdata=[]
        if level==0 and currlevel>1:
            return bufferdata
        for bomid in component.product_tmpl_id.bom_ids:
            for bomline in bomid.bom_line_ids:
                children=self._getChildrenBom(cr, uid, bomline.product_id, level, currlevel+1, context=context)
                bufferdata.extend(children)
                bufferdata.append(bomline.product_id.id)
        result.extend(bufferdata)
        return list(set(result))

    def RegMessage(self, cr, uid, request, default=None, context=None):
        """
            Registers a message for requested component
        """
        oid, message = request
        self.wf_message_post(cr, uid, [oid], body=_(message))
        return False

    def getLastTime(self, cr, uid, oid, default=None, context=None):
        return self.getUpdTime(self.browse(cr, uid, oid, context=context))

    def getUpdTime(self, obj):
        if(obj.write_date!=False):
            return datetime.strptime(obj.write_date,'%Y-%m-%d %H:%M:%S')
        else:
            return datetime.strptime(obj.create_date,'%Y-%m-%d %H:%M:%S')

##  Customized Automations
    def on_change_name(self, cr, uid, oid, name=False, engineering_code=False):
        if name:
            results=self.search(cr,uid,[('name','=',name)])
            if len(results) > 0:
                raise UserError(_("Part %s already exists.\nClose with OK to reuse, with Cancel to discharge." %(name)))
            if not engineering_code:
                return {'value': {'engineering_code': name}}            
        return {}

##  External methods
    def Clone(self, cr, uid, oid, context={}, defaults={}):
        """
            create a new revision of the component
        """
        exitValues = {}
        newID = self.copy(cr, uid, oid, defaults, context)
        if newID not in (None, False):
            newEnt = self.browse(cr, uid, newID, context=context)
            exitValues['_id'] = newID
            exitValues['name'] = newEnt.name
            exitValues['engineering_code'] = newEnt.engineering_code
            exitValues['engineering_revision'] = newEnt.engineering_revision
        return exitValues

    def GetUpdated(self,cr,uid,vals,context=None):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        partData, attribNames = vals
        ids=self.GetLatestIds(cr, uid, partData, context)
        return self.read(cr, uid, list(set(ids)), attribNames)
    
    def GetLatestIds(self,cr,uid,vals,context=None):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        ids=[]
        for partName, partRev, updateDate in vals:
            if updateDate:
                if partRev == None or partRev == False:
                    partIds=self.search(cr,uid,[('engineering_code','=',partName),('write_date','>',updateDate)],order='engineering_revision',context=context)
                    if len(partIds)>0:
                        partIds.sort()
                        ids.append(partIds[len(partIds)-1])
                else:
                    ids.extend(self.search(cr,uid,[('engineering_code','=',partName),('engineering_revision','=',partRev),('write_date','>',updateDate)],context=context))
            else:
                if partRev == None or partRev == False:
                    partIds=self.search(cr,uid,[('engineering_code','=',partName)],order='engineering_revision',context=context)
                    if len(partIds)>0:
                        partIds.sort()
                        ids.append(partIds[len(partIds)-1])
                else:
                    ids.extend(self.search(cr,uid,[('engineering_code','=',partName),('engineering_revision','=',partRev)],context=context))
        return list(set(ids))

    def NewRevision(self, cr, uid, ids, context=None):
        """
            create a new revision of current component
        """
        newID=None
        newIndex=0
        for tmpObject in self.browse(cr, uid, ids, context=context):
            latestIDs=self.GetLatestIds(cr, uid,[(tmpObject.engineering_code,tmpObject.engineering_revision,False)], context=context)
            for oldObject in self.browse(cr, uid, latestIDs, context=context):
                newIndex=int(oldObject.engineering_revision)+1
                defaults={}
                defaults['engineering_writable']=False
                defaults['state']='undermodify'
                self.write(cr, uid, [oldObject.id], defaults, context=context, check=False)
                self.wf_message_post(cr, uid, [oldObject.id], body=_('Status moved to: %s.' %(USEDIC_STATES[defaults['state']])))
                # store updated infos in "revision" object
                defaults['name']=oldObject.name                 # copy function needs an explicit name value
                defaults['engineering_revision']=newIndex
                defaults['engineering_writable']=True
                defaults['state']='draft'
                defaults['linkeddocuments']=[]                  # Clean attached documents for new revision object
                newID=self.copy(cr, uid, oldObject.id, defaults, context=context)
                self.wf_message_post(cr, uid, [oldObject.id], body=_('Created : New Revision.'))
                self.write(cr,uid,[newID],{'name':oldObject.name},check=False,context=None)
                # create a new "old revision" object
                break
            break
        return (newID, newIndex)

    def SaveOrUpdate(self, cr, uid, vals, context={}):
        """
            Save or Update Parts
        """
        listedParts = []
        retValues = []
        for part in vals:
            hasSaved=False
            if part['engineering_code'] in listedParts:
                continue
            if not ('engineering_code' in part) or (not 'engineering_revision' in part):
                part['componentID']=False
                part['hasSaved']=hasSaved
                continue
            existingID=self.search(cr,uid,[
                                           ('engineering_code','=',part['engineering_code'])
                                          ,('engineering_revision','=',part['engineering_revision'])],
                                   context=context)
            if not existingID:
                existingID=self.create(cr,uid,part)
                hasSaved=True
            else:
                existingID=existingID[0]
                objPart=self.browse(cr, uid, existingID, context=context)
                part['name']=objPart.name
                if (self.getUpdTime(objPart)<datetime.strptime(part['lastupdate'],'%Y-%m-%d %H:%M:%S')):
                    if self._iswritable(cr,uid,objPart):
                        del(part['lastupdate'])
                        if not self.write(cr,uid,[existingID], part , context=context):
                            raise UserError(_("Part %r cannot be updated" % (part['engineering_code'])))
                        hasSaved=True
            part['componentID']=existingID
            part['hasSaved']=hasSaved
            retValues.append(part)
            listedParts.append(part['engineering_code'])
        return retValues 


    def QueryLast(self, cr, uid, request=([],[]), default=None, context=None):
        """
            Query to return values based on columns selected.
        """
        objId=False
        expData=[]
        queryFilter, columns = request
        if len(columns)<1:
            return expData
        if 'engineering_revision' in queryFilter:
            del queryFilter['engineering_revision']
        allIDs=self.search(cr,uid,queryFilter,order='engineering_revision',context=context)
        if len(allIDs)>0:
            allIDs.sort()
            objId=allIDs[len(allIDs)-1]
        if objId:
            tmpData=self.export_data(cr, uid, [objId], columns)
            if 'datas' in tmpData:
                expData=tmpData['datas']
        return expData

    def create_bom_from_ebom(self, cr, uid, objProductProductBrw, newBomType, context={}):
        """
            create a new bom starting from ebom
        """
        if newBomType not in ['normal', 'spbom']:
            raise UserError(_("Could not convert source bom to %r" % newBomType))
        product_template_id = objProductProductBrw.product_tmpl_id.id
        bomType = self.pool.get('mrp.bom')
        bomLType = self.pool.get('mrp.bom.line')
        bomIds = bomType.search(cr, uid, [('product_tmpl_id', '=', product_template_id),
                                          ('type', '=', newBomType)])
        if bomIds:
            for bom_line in bomType.browse(cr, uid, bomIds[0], context=context).bom_line_ids:
                self.create_bom_from_ebom(cr, uid, bom_line.product_id, newBomType, context)
        else:
            idNewTypeBoms = bomType.search(cr, uid, [('product_tmpl_id', '=', product_template_id),
                                                     ('type', '=', 'ebom')])
            if not idNewTypeBoms:
                UserError(_("No Enginnering bom provided"))
            for newBomId in idNewTypeBoms:
                newidBom = bomType.copy(cr, uid, newBomId, {}, context)
                bomType.write(cr, uid, [newidBom], {'name': objProductProductBrw.name,
                                                    'product_tmpl_id': product_template_id,
                                                    'type': newBomType}, check=False, context=None)
                oidBom = bomType.browse(cr, uid, newidBom, context=context)
                ok_rows = self._summarizeBom(cr, uid, oidBom.bom_line_ids)
                # remove not summarised lines
                for bom_line in list(set(oidBom.bom_line_ids) ^ set(ok_rows)):
                    bomLType.unlink(cr, uid, [bom_line.id], context=None)
                # update the quantity with the summarised values
                for bom_line in ok_rows:
                    bomLType.write(cr, uid, [bom_line.id], {'type': newBomType,
                                                            'source_id': False,
                                                            'product_qty': bom_line.product_qty, }, context=None)
                    self.create_bom_from_ebom(cr, uid, bom_line.product_id, newBomType, context)
                self.wf_message_post(cr, uid, [objProductProductBrw.id], body=_('Created %r' % newBomType))
                break

    #  Menu action Methods
    def _create_normalBom(self, cr, uid, idd, context=None):
        """
            Create a new Normal Bom (recursive on all EBom children)
        """
        defaults={}
        if idd in self.processedIds:
            return False
        checkObj=self.browse(cr, uid, idd, context)
        if not checkObj:
            return False
        bomType = self.pool.get('mrp.bom')
        bomLType = self.pool.get('mrp.bom.line')
        product_template_id = checkObj.product_tmpl_id.id
        objBoms = bomType.search(cr, uid, [('product_tmpl_id','=',product_template_id),('type','=','normal')])
        idBoms = bomType.search(cr, uid, [('product_tmpl_id','=',product_template_id),('type','=','ebom')])

        if not objBoms:
            idBoms = bomType.search(cr, uid, [('product_tmpl_id', '=', product_template_id),
                                              ('type', '=', 'ebom')])
            if idBoms:
                self.processedIds.append(idd)
                newidBom=bomType.copy(cr, uid, idBoms[0], defaults, context)
                if newidBom:
                    bomType.write(cr,uid,[newidBom],{'name':checkObj.name,'product_id':checkObj.id,'type':'normal',},check=False,context=None)
                    oidBom=bomType.browse(cr,uid,newidBom,context=context)
                    ok_rows=self._summarizeBom(cr, uid, oidBom.bom_line_ids)
                    for bom_line in list(set(oidBom.bom_line_ids) ^ set(ok_rows)):
                        bomLType.unlink(cr,uid,[bom_line.id],context=None)
                    for bom_line in ok_rows:
                        bomLType.write(cr,uid,[bom_line.id],{'type':'normal','source_id':False,'name':bom_line.product_id.name,'product_qty':bom_line.product_qty,},context=None)
                        self._create_normalBom(cr, uid, bom_line.product_id.id, context)
        else:
            for bom_line in bomType.browse(cr, uid, objBoms[0], context=context).bom_line_ids:
                self._create_normalBom(cr, uid, bom_line.product_id.id, context)
        return False

    def _summarizeBom(self, cr, uid, datarows):
        dic = {}
        for datarow in datarows:
            key = str(datarow.product_id.id)
            if key in dic:
                dic[key].product_qty = float(dic[key].product_qty) + float(datarow.product_qty)
            else:
                dic[key] = datarow
        retd = dic.values()
        return retd

#  Work Flow Internal Methods
    def _get_recursive_parts(self, cr, uid, ids, excludeStatuses, includeStatuses):
        """
           Get all ids related to current one as children
        """
        errors = []
        tobeReleasedIDs = []
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        tobeReleasedIDs.extend(ids)
        children = []
        for oic in self.browse(cr, uid, ids, context=None):
            children = self.browse(cr, uid, self._getChildrenBom(cr, uid, oic, 1))
            for child in children:
                if (child.state not in excludeStatuses) and (child.state not in includeStatuses):
                    errors.append(_("Product code: %r revision %r ") & (child.engineering_code, child.engineering_revision))
                    continue
                if child.state in includeStatuses:
                    if child.id not in tobeReleasedIDs:
                        tobeReleasedIDs.append(child.id)
        msg = ''
        if errors:
            msg = _("Unable to perform workFlow action due")
            for subMsg in errors:
                msg = "\n" + subMsg
        return (msg, list(set(tobeReleasedIDs)))

    def action_create_normalBom_WF(self, cr, uid, ids, context=None):
        """
            Create a new Normal Bom if doesn't exist (action callable from code)
        """
        for idd in ids:
            self.processedIds = []
            self._create_normalBom(cr, uid, idd, context)
        self.wf_message_post(cr, uid, ids, body=_('Created Normal Bom.'))
        return False

    def _action_ondocuments(self,cr,uid,ids,action_name,context=None):
        """
            move workflow on documents having the same state of component 
        """
        docIDs = []
        try:
            documentType=self.pool.get('plm.document')
            for oldObject in self.browse(cr, uid, ids, context=context):
                if (action_name!='transmit') and (action_name!='reject') and (action_name!='release'):
                    check_state=oldObject.state
                else:
                    check_state='confirmed'
                for document in oldObject.linkeddocuments:
                    if document.state == check_state:
                        if document.is_checkout:
                            logging.warning("Unable to perform workflow operation for document %r" % document.id)
                            continue
                        if document.id not in docIDs:
                            docIDs.append(document.id)
            if len(docIDs)>0:
                if action_name=='confirm':
                    documentType.signal_workflow(cr, uid, docIDs, action_name)
                elif action_name=='transmit':
                    documentType.signal_workflow(cr, uid, docIDs, 'confirm')
                elif action_name=='draft':
                    documentType.signal_workflow(cr, uid, docIDs, 'correct')
                elif action_name=='correct':
                    documentType.signal_workflow(cr, uid, docIDs, action_name)
                elif action_name=='reject':
                    documentType.signal_workflow(cr, uid, docIDs, 'correct')
                elif action_name=='release':
                    documentType.signal_workflow(cr, uid, docIDs, action_name)
                elif action_name=='undermodify':
                    documentType.action_cancel(cr,uid,docIDs)
                elif action_name=='suspend':
                    documentType.action_suspend(cr,uid,docIDs)
                elif action_name=='reactivate':
                    documentType.signal_workflow(cr, uid, docIDs, 'release')
                elif action_name=='obsolete':
                    documentType.signal_workflow(cr, uid, docIDs, action_name)
        except Exception, ex:
            logging.error(ex)
        return docIDs
            
    def _iswritable(self, cr, user, oid):
        checkState=('draft')
        if not oid.engineering_writable:
            logging.warning("_iswritable : Part (%r - %d) is not writable." %(oid.engineering_code,oid.engineering_revision))
            return False
        if not oid.state in checkState:
            logging.warning("_iswritable : Part (%r - %d) is in status %r." %(oid.engineering_code,oid.engineering_revision,oid.state))
            return False
        if oid.engineering_code == False:
            logging.warning("_iswritable : Part (%r - %d) is without Engineering P/N." %(oid.name,oid.engineering_revision))
            return False
        return True  

    def wf_message_post(self,cr,uid,ids,body='',context=None):
        """
            Writing messages to follower, on multiple objects
        """
        if not (body==''):
            for id in ids:
                self.message_post(cr, uid, [id], body=_(body))
        
    def action_draft(self,cr,uid,ids,context=None):
        """
            release the object
        """
        defaults={}
        status='draft'
        action='draft'
        docaction='draft'
        defaults['engineering_writable']=True
        defaults['state']=status
        excludeStatuses=['draft','released','undermodify','obsoleted']
        includeStatuses=['confirmed','transmitted']
        return self._action_to_perform(cr, uid, ids, status, action, docaction, defaults, excludeStatuses, includeStatuses, context)

    def action_confirm(self,cr,uid,ids,context=None):
        """
            action to be executed for Draft state
        """
        defaults={}
        status='confirmed'
        action='confirm'
        docaction='confirm'
        defaults['engineering_writable']=False
        defaults['state']=status
        excludeStatuses=['confirmed','transmitted','released','undermodify','obsoleted']
        includeStatuses=['draft']
        return self._action_to_perform(cr, uid, ids, status, action, docaction, defaults, excludeStatuses, includeStatuses, context)

    def action_release(self,cr,uid,ids,context=None):
        """
           action to be executed for Released state
        """
        tmpl_ids=[]
        full_ids=[]
        defaults={}
        prodTmplType=self.pool.get('product.template')
        excludeStatuses=['released','undermodify','obsoleted']
        includeStatuses=['confirmed']
        errors, allIDs = self._get_recursive_parts(cr, uid, ids, excludeStatuses, includeStatuses)
        if len(allIDs) < 1 or len(errors) > 0:
            raise UserError(errors)
        allProdObjs=self.browse(cr, uid, allIDs, context=context)
        for oldObject in allProdObjs:
            last_id=self._getbyrevision(cr, uid, oldObject.engineering_code, oldObject.engineering_revision-1)
            if last_id != None:
                defaults['engineering_writable']=False
                defaults['state']='obsoleted'
                prodObj=self.browse(cr, uid, [last_id], context=context)
                prodTmplType.write(cr,uid,[prodObj.product_tmpl_id.id],defaults ,context=context)
                self.wf_message_post(cr, uid, [last_id], body=_('Status moved to: %s.' %(USEDIC_STATES[defaults['state']])))
            defaults['engineering_writable']=False
            defaults['state']='released'
        self._action_ondocuments(cr,uid,allIDs,'release')
        for currId in allProdObjs:
            if not(currId.id in ids):
                tmpl_ids.append(currId.product_tmpl_id.id)
            full_ids.append(currId.product_tmpl_id.id)
        self.signal_workflow(cr, uid, tmpl_ids, 'release')
        objId = self.pool.get('product.template').write(cr, uid, full_ids, defaults, context=context)
        if (objId):
            self.wf_message_post(cr, uid, allIDs, body=_('Status moved to: %s.' %(USEDIC_STATES[defaults['state']])))
        return objId

    def action_obsolete(self,cr,uid,ids,context=None):
        """
            obsolete the object
        """
        defaults={}
        status='obsoleted'
        action='obsolete'
        docaction='obsolete'
        defaults['engineering_writable']=False
        defaults['state']=status
        excludeStatuses=['draft','confirmed','transmitted','undermodify','obsoleted']
        includeStatuses=['released']
        return self._action_to_perform(cr, uid, ids, status, action, docaction, defaults, excludeStatuses, includeStatuses, context)

    def action_reactivate(self,cr,uid,ids,context=None):
        """
            reactivate the object
        """
        defaults={}
        status='released'
        action=''
        docaction='release'
        defaults['engineering_writable']=True
        defaults['state']=status
        excludeStatuses=['draft','confirmed','transmitted','released','undermodify','obsoleted']
        includeStatuses=['obsoleted']
        return self._action_to_perform(cr, uid, ids, status, action, docaction, defaults, excludeStatuses, includeStatuses, context)
    
#   WorkFlow common internal method to apply changes

    def _action_to_perform(self, cr, uid, ids, status, action, docaction, defaults=[], excludeStatuses=[], includeStatuses=[], context=None):
        tmpl_ids=[]
        full_ids=[]
        userErrors, allIDs = self._get_recursive_parts(cr, uid, ids, excludeStatuses, includeStatuses)
        if userErrors:
            UserError(userErrors)
        self._action_ondocuments(cr,uid,allIDs,docaction)
        for currId in self.browse(cr,uid,allIDs,context=context):
            if not(currId.id in ids):
                tmpl_ids.append(currId.product_tmpl_id.id)
            full_ids.append(currId.product_tmpl_id.id)
        if action:
            self.signal_workflow(cr, uid, tmpl_ids, action)
        objId=self.pool.get('product.template').write(cr, uid, full_ids, defaults, context=context)
        if (objId):
            self.wf_message_post(cr, uid, allIDs, body=_('Status moved to: %s.' % (USEDIC_STATES[defaults['state']])))
        return objId
    
#######################################################################################################################################33

#   Overridden methods for this entity

    def create(self, cr, uid, vals, context=None):
        if not vals:
            raise ValidationError(_("""You are trying to create a product without values"""))
        if ('name' in vals):
            if not vals['name']:
                return False
            existingIDs = self.search(cr, uid, [('name', '=', vals['name'])], order='engineering_revision', context=context)
            if 'engineering_code' in vals:
                if vals['engineering_code'] == False:
                    vals['engineering_code'] = vals['name']
            else:
                vals['engineering_code'] = vals['name']
            if existingIDs:
                existingID = existingIDs[len(existingIDs) - 1]
                if ('engineering_revision' in vals):
                    existObj = self.browse(cr, uid, existingID, context=context)
                    if existObj:
                        if vals['engineering_revision'] > existObj.engineering_revision:
                            vals['name'] = existObj.name
                        else:
                            return existingID
                else:
                    return existingID
        try:
            return super(plm_component, self).create(cr, uid, vals, context=context)
        except Exception, ex:
            import psycopg2
            if isinstance(ex, psycopg2.IntegrityError):
                raise ex
            raise ValidationError(_(" (%r). It has tried to create with values : (%r).") % (ex, vals))

    def copy(self, cr, uid, oid, defaults={}, context=None):
        """
            Overwrite the default copy method
        """
        previous_name=self.browse(cr,uid,oid,context=context).name
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
        objId = super(plm_component,self).copy(cr,uid,oid,defaults,context=context)
        if (objId):
            self.wf_message_post(cr, uid, [oid], body=_('Copied starting from : %s.' %previous_name))
        return objId

    def unlink(self, cr, uid, ids, context=None):
        values={'state':'released',}
        checkState=('undermodify','obsoleted')
        for checkObj in self.browse(cr, uid, ids, context=context):
            existingID = self.search(cr, uid, [('engineering_code', '=', checkObj.engineering_code),('engineering_revision', '=', checkObj.engineering_revision-1)])
            if len(existingID)>0:
                oldObject=self.browse(cr, uid, existingID[0], context=context)
                if oldObject.state in checkState:
                    self.wf_message_post(cr, uid, [oldObject.id], body=_('Removed : Latest Revision.'))
                    if not self.write(cr, uid, [oldObject.id], values, context, check=False):
                        logging.warning("unlink : Unable to update state to old component (%r - %d)." %(oldObject.engineering_code,oldObject.engineering_revision))
                        return False
        return super(plm_component,self).unlink(cr, uid, ids, context=context)

#   Overridden methods for this entity

    def translateForClient(self, cr, uid, values=[], forcedLang='', context={}):
        '''
            Get values attribute in this format:
            values = [{'field1':value1,'field2':value2,...}]     only one element in the list!!!
            and return computed values due to language
            
            Get also forcedLang attribute in this format:
            forcedLang = 'en_US'
            if is not set it takes language from user
        '''
        language = forcedLang
        if not forcedLang:
            resDict = self.pool.get('res.users').read(cr, uid, uid, ['lang'])
            language = resDict.get('lang','')
        if values:
            values = values[0]
        if language and values:
            toRead = filter(lambda x: type(x) in [str, unicode] and x,values.values()) # Where computed only string and not null string values (for performance improvement)
            toRead = list(set(toRead))                                                 # Remove duplicates
            for fieldName, valueToTranslate in values.items():
                if valueToTranslate not in toRead:
                    continue
                translationObj = self.pool.get('ir.translation')
                resIds = translationObj.search(cr, uid, [('lang','=',language),('src','=',valueToTranslate)])
                if resIds:
                    readDict = translationObj.read(cr, uid, resIds[0], ['value'])
                    values[fieldName] = readDict.get('value','')
        return values

plm_component()

class PlmComponentRevisionWizard(models.Model):
    _name = 'product.rev_wizard'
    
    @api.multi
    def action_create_new_revision_by_server(self):
        def stateAllows(brwsObj, objType):
            if brwsObj.state != 'released':
                logging.error('[action_create_new_revision_by_server:stateAllows] Cannot revise obj %s, Id: %r because state is %r' % (objType, brwsObj.id, brwsObj.state))
                raise UserError(_("%s cannot be revised because the state isn't released!" % (objType)))
            return True
        product_id = self.env.context.get('default_product_id', False)
        if not product_id:
            logging.error('[action_create_new_revision_by_server] Cannot revise because product_id is %r' % (product_id))
            raise UserError(_('Current component cannot be revised!'))
        prodProdEnv = self.env['product.product']
        prodBrws = prodProdEnv.browse(product_id)
        if stateAllows(prodBrws, 'Component'):
            revRes = prodBrws.NewRevision()
            newID, newIndex = revRes
            newIndex
            if not newID:
                logging.error('[action_create_new_revision_by_server] newID: %r' % (newID))
                raise UserError(_('Something wrong happens during new component revision process.'))
            createdDocIds = []
            for docBrws in prodBrws.linkeddocuments:
                if stateAllows(docBrws, 'Document'):
                    resDoc = docBrws.NewRevision()
                    newDocID, newDocIndex = resDoc
                    newDocIndex
                    if not newDocID:
                        logging.error('[action_create_new_revision_by_server] newDocID: %r' % (newDocID))
                        raise UserError(_('Something wrong happens during new document revision process.'))
                    createdDocIds.append(newDocID)
            prodProdEnv.browse(newID).linkeddocuments = createdDocIds
            return {'name': _('Revised Product'),
                    'view_type': 'tree,form',
                    "view_mode": 'form',
                    'res_model': 'product.product',
                    'res_id': newID,
                    'type': 'ir.actions.act_window'}
    
PlmComponentRevisionWizard()