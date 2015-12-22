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

import sys
import types
import logging

import openerp.addons.decimal_precision as dp
from openerp        import models, fields, api, SUPERUSER_ID, _, osv
_logger         =   logging.getLogger(__name__)

# To be adequated to plm.document class states
USED_STATES=[('draft',_('Draft')),('confirmed',_('Confirmed')),('released',_('Released')),('undermodify',_('UnderModify')),('obsoleted',_('Obsoleted'))]

class plm_config_settings(models.Model):
    _name = 'plm.config.settings'
    _inherit = 'res.config.settings'

    plm_service_id  =   fields.Char(_('Register PLM module, insert your Service ID.'),  size=128,  help=_("Insert the Service ID and register your PLM module. Ask it to OmniaSolutions."))
    activated_id    =   fields.Char(_('Activated PLM client'),                          size=128,  help=_("Listed activated Client."))
    active_editor   =   fields.Char(_('Client Editor Name'),                            size=128,  help=_("Used Editor Name"))
    active_node     =   fields.Char(_('OS machine name'),                               size=128,  help=_("Editor Machine name"))
    active_os       =   fields.Char(_('OS name'),                                       size=128,  help=_("Editor OS name"))
    active_os_rel   =   fields.Char(_('OS release'),                                    size=128,  help=_("Editor OS release"))
    active_os_ver   =   fields.Char(_('OS version'),                                    size=128,  help=_("Editor OS version"))
    active_os_arch  =   fields.Char(_('OS architecture'),                               size=128,  help=_("Editor OS architecture"))
    node_id         =   fields.Char(_('Registered PLM client'),                         size=128,  help=_("Listed registered Client."))

 
    def GetServiceIds(self, cr, uid, oids, default=None, context=None):
        """
            Get all Service Ids registered.
        """
        ids=[]
        partIds=self.search(cr,uid,[('activated_id','=',False)],context=context)
        for part in self.browse(cr, uid, partIds):
            ids.append(part.plm_service_id)
        return list(set(ids))
 
    def RegisterActiveId(self, cr, uid, vals, default=None, context=None):
        """
            Get all Service Ids registered.  [serviceID, activation, activeEditor, (system, node, release, version, machine, processor) ]
        """
        defaults={}
        serviceID, activation, activeEditor, platformData, nodeId=vals
        if activation:
            defaults['plm_service_id']=serviceID
            defaults['activated_id']=activation
            defaults['active_editor']=activeEditor
            defaults['active_os']=platformData[0]
            defaults['active_node']=platformData[1]
            defaults['active_os_rel']=platformData[2]
            defaults['active_os_ver']=platformData[3]
            defaults['active_os_arch']=platformData[4]
            defaults['node_id']=nodeId
    
            partIds=self.search(cr,uid,[('plm_service_id','=',serviceID),('activated_id','=',activation)],context=context)
    
            if partIds:
                for partId  in partIds:
                    self.write(cr, uid, [partId], defaults, context=context)
                    return False
            
            self.create(cr, uid, defaults, context=context)
        return False
   
    def GetActiveServiceId(self, cr, uid, vals, default=None, context=None):
        """
            Get all Service Ids registered.  [serviceID, activation, activeEditor, (system, node, release, version, machine, processor) ]
        """
        results=[]
        nodeId, activation, activeEditor, platformData =vals

        partIds=self.search(cr,uid,[('node_id','=',nodeId),('activated_id','=',activation)],context=context)

        for partId  in self.browse(cr, uid, partIds):
            results.append(partId.plm_service_id)
            
        return results

plm_config_settings()
    
class plm_component(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'
    
    state                   =   fields.Selection    (USED_STATES,_('Status'), help=_("The status of the product in its LifeCycle."), readonly="True")
    engineering_code        =   fields.Char         (_('Part Number'),help=_("This is engineering reference to manage a different P/N from item Name."),size=64)
    engineering_revision    =   fields.Integer      (_('Revision'), required=True,help=_("The revision of the product."))
    engineering_writable    =   fields.Boolean      (_('Writable'))
    engineering_material    =   fields.Char         (_('Raw Material'),size=128,required=False,help=_("Raw material for current product, only description for titleblock."))
    #engineering_treatment    =    fields.Char        (_('Treatment'),size=64,required=False,help=_("Thermal treatment for current product"))
    engineering_surface     =   fields.Char         (_('Surface Finishing'),size=128,required=False,help=_("Surface finishing for current product, only description for titleblock."))

    _defaults = {
                 'state': lambda *a: 'draft',
                 #'engineering_revision': lambda self,ctx:0,
                 #'engineering_writable': lambda *a: True,
                 'engineering_revision':0,
                 'engineering_writable': True,
                 'type': 'product',
                 'standard_price': 0,
                 'volume':0,
                 'weight':0,
                 'cost_method':0,
                 'sale_ok':0,
                 'state':'draft',
                 'mes_type':'fixed',
                 'cost_method':'standard',
    }
    _sql_constraints = [
        ('partnumber_uniq', 'unique (engineering_code,engineering_revision)', _('Part Number has to be unique!'))
    ]
    
    def init(self, cr):
        cr.execute("""
-- Index: product_template_engcode_index

DROP INDEX IF EXISTS product_template_engcode_index;

CREATE INDEX product_template_engcode_index
  ON product_template
  USING btree
  (engineering_code);
  """)
  
        cr.execute("""
-- Index: product_template_engcoderev_index

DROP INDEX IF EXISTS product_template_engcoderev_index;

CREATE INDEX product_template_engcoderev_index
  ON product_template
  USING btree
  (engineering_code, engineering_revision);
  """)

plm_component()

class plm_component_document_rel(models.Model):
    _name = 'plm.component.document.rel'
    _description = "Component Document Relations"
    
    component_id    =   fields.Many2one('product.product', _('Linked Component'), ondelete='cascade')
    document_id     =   fields.Many2one('plm.document', _('Linked Document'), ondelete='cascade')

    _sql_constraints = [
        ('relation_unique', 'unique(component_id,document_id)', _('Component and Document relation has to be unique !')),
    ]

    def SaveStructure(self, cr, uid, relations, level=0, currlevel=0):
        """
            Save Document relations
        """
        def cleanStructure(relations):
            res=[]
            for document_id,component_id in relations:
                latest=(document_id,component_id)
                if latest in res:
                    continue
                res.append(latest)
                ids=self.search(cr,uid,[('document_id','=',document_id),('component_id','=',component_id)])
                if ids:
                    self.unlink(cr,uid,ids)

        def saveChild(args):
            """
                save the relation 
            """
            try:
                res={}
                res['document_id'],res['component_id']=args
                self.create(cr, uid, res)
            except:
                logging.warning("saveChild : Unable to create a link. Arguments (%s)." %(str(args)))
                raise Exception(_("saveChild: Unable to create a link."))
            
        if len(relations)<1: # no relation to save 
            return False
        cleanStructure(relations)
        for relation in relations:
            saveChild(relation)
        return False

plm_component_document_rel()

         
class plm_relation_line(models.Model):
    _name = 'mrp.bom.line'
    _inherit = 'mrp.bom.line'
    
    create_date     = fields.Datetime(_('Creation Date'), readonly=True)
    source_id       = fields.Many2one('plm.document','name',ondelete='no action', readonly=True,help=_("This is the document object that declares this BoM."))
    type            = fields.Selection([('normal',_('Normal BoM')),('phantom',_('Sets / Phantom')),('ebom',_('Engineering BoM')),('spbom',_('Spare BoM'))], _('BoM Type'), required=True, help=
        _("Use a phantom bill of material in raw materials lines that have to be " \
        "automatically computed in on production order and not one per level." \
        "If you put \"Phantom/Set\" at the root level of a bill of material " \
        "it is considered as a set or pack: the products are replaced by the components " \
        "between the sale order to the picking without going through the production order." \
        "The normal BoM will generate one production order per BoM level."))
    itemnum         = fields.Integer(_('CAD Item Position'),help=_("This is the item reference position into the CAD document that declares this BoM."))
    itemlbl         = fields.Char(_('CAD Item Position Label'),size=64)
                
    _defaults = {
        'product_uom' : 1,
    }
    
    _order = 'itemnum'
        
plm_relation_line()

class plm_relation(models.Model):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

    create_date      =   fields.Datetime(_('Creation Date'), readonly=True)
    source_id        =   fields.Many2one('plm.document','name',ondelete='no action',readonly=True,help=_('This is the document object that declares this BoM.'))
    type             =   fields.Selection([('normal',_('Normal BoM')),('phantom',_('Sets / Phantom')),('ebom',_('Engineering BoM')),('spbom',_('Spare BoM'))], _('BoM Type'), required=True, help=
                    _("Use a phantom bill of material in raw materials lines that have to be " \
                    "automatically computed on a production order and not one per level." \
                    "If you put \"Phantom/Set\" at the root level of a bill of material " \
                    "it is considered as a set or pack: the products are replaced by the components " \
                    "between the sale order to the picking without going through the production order." \
                    "the normal bom will generate one production order per bom level."))
    weight_net      =   fields.Float('Weight',digits_compute=dp.get_precision(_('Stock Weight')), help=_("The BoM net weight in Kg."))

    _defaults = {
        'product_uom' : 1,
        'weight_net' : 0.0,
    }

    def init(self, cr):
        self._packed=[]

    def _getinbom(self, cr, uid, pid, sid=False):
        bomLType=self.pool.get('mrp.bom.line')
        ids=bomLType.search(cr,uid,[('product_id','=',pid),('source_id','=',sid),('type','=','ebom')])
        if not ids:
            ids=bomLType.search(cr,uid,[('product_id','=',pid),('source_id','=',sid),('type','=','normal')])
            if not ids:
                ids=bomLType.search(cr,uid,[('product_id','=',pid),('source_id','=',False),('type','=','ebom')])
            if not ids:
                ids=bomLType.search(cr,uid,[('product_id','=',pid),('source_id','=',False),('type','=','normal')])
                if not ids:
                    ids=bomLType.search(cr,uid,[('product_id','=',pid),('type','=','ebom')])
                if not ids:
                    ids=bomLType.search(cr,uid,[('product_id','=',pid),('type','=','normal')])
        return bomLType.browse(cr,uid,list(set(ids)),context=None)

    def _getbom(self, cr, uid, pid, sid=False):
        if sid==None:
            sid=False
        ids=self.search(cr,uid,[('product_tmpl_id','=',pid),('source_id','=',sid),('type','=','ebom')])
        if not ids:
            ids=self.search(cr,uid,[('product_tmpl_id','=',pid),('source_id','=',sid),('type','=','normal')])
            if not ids:
                ids=self.search(cr,uid,[('product_tmpl_id','=',pid),('source_id','=',False),('type','=','ebom')])
                if not ids:
                    ids=self.search(cr,uid,[('product_tmpl_id','=',pid),('source_id','=',False),('type','=','normal')])
                    if not ids:
                        ids=self.search(cr,uid,[('product_tmpl_id','=',pid),('type','=','ebom')])
                        if not ids:
                            ids=self.search(cr,uid,[('product_tmpl_id','=',pid),('type','=','normal')])
        return self.browse(cr,uid,list(set(ids)),context=None)

    def _getpackdatas(self, cr, uid, relDatas):
        prtDatas={}
        tmpbuf=(((str(relDatas).replace('[','')).replace(']','')).replace('(','')).replace(')','').split(',')
        tmpids=[int(tmp) for tmp in tmpbuf if len(tmp.strip()) > 0]
        if len(tmpids)<1:
            return prtDatas
        compType=self.pool.get('product.product')
        tmpDatas=compType.read(cr, uid, tmpids)
        for tmpData in tmpDatas:
            for keyData in tmpData.keys():
                if tmpData[keyData]==None:
                    del tmpData[keyData]
            prtDatas[str(tmpData['id'])]=tmpData
        return prtDatas

    def _getpackreldatas(self, cr, uid, relDatas, prtDatas):
        relids={}
        relationDatas={}
        tmpbuf=(((str(relDatas).replace('[','')).replace(']','')).replace('(','')).replace(')','').split(',')
        tmpids=[int(tmp) for tmp in tmpbuf if len(tmp.strip()) > 0]
        if len(tmpids)<1:
            return prtDatas
        for keyData in prtDatas.keys():
            tmpData=prtDatas[keyData]
            if len(tmpData['bom_ids'])>0:
                relids[keyData]=tmpData['bom_ids'][0]

        if len(relids)<1:
            return relationDatas
        setobj=self.pool.get('mrp.bom')
        for keyData in relids.keys():
            relationDatas[keyData]=setobj.read(cr, uid, relids[keyData])
        return relationDatas

    def GetWhereUsed(self, cr, uid, ids, context=None):
        """
            Return a list of all fathers of a Part (all levels)
        """
        self._packed=[]
        relDatas=[]
        if len(ids)<1:
            return None
        sid=False        
        if len(ids)>1:
            sid=ids[1]
        oid=ids[0]
        relDatas.append(oid)
        relDatas.append(self._implodebom(cr, uid, self._getinbom(cr, uid, oid, sid)))
        prtDatas=self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))
    
    def GetExplose(self, cr, uid, ids, context=None):
        """
            Returns a list of all children in a Bom (all levels)
        """
        self._packed=[]
        relDatas=[ids[0],self._explodebom(cr, uid, self._getbom(cr, uid, ids[0]), False)]
        prtDatas=self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def _explodebom(self, cr, uid, bids, check=True):
        """
            Explodes a bom entity  ( check=False : all levels, check=True : one level )
        """
        output=[]
        for bid in bids:
            for bom_line in bid.bom_line_ids:
                if check and (bom_line.product_id.id in self._packed):
                    continue
                innerids=self._explodebom(cr, uid, self._getbom(cr, uid, bom_line.product_id.id), check)
                self._packed.append(bom_line.product_id.id)
                output.append([bom_line.product_id.id, innerids])
        return(output)

    def GetExploseSum(self, cr, uid, ids, context=None):
        """
            Return a list of all children in a Bom taken once (all levels)
        """
        self._packed=[]
        relDatas=[ids[0],self._explodebom(cr, uid, self._getbom(cr, uid, ids[0]), True)]
        prtDatas=self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def _implodebom(self, cr, uid, bomObjs):
        """
            Execute implosion for a a bom object
        """
        pids=[]
        for bomObj in bomObjs:
            if not bomObj.bom_id:
                continue
            if bomObj.bom_id.id in self._packed:
                continue
            self._packed.append(bomObj.bom_id.id)
            bomFthObj=self.browse(cr,uid,[bomObj.bom_id.id],context=None)
            innerids=self._implodebom(cr, uid, self._getinbom(cr, uid, bomFthObj.product_tmpl_id.id))
            pids.append((bomFthObj.product_tmpl_id.id,innerids))
        return (pids)

    def GetWhereUsedSum(self, cr, uid, ids, context=None):
        """
            Return a list of all fathers of a Part (all levels)
        """
        self._packed=[]
        relDatas=[]
        if len(ids)<1:
            return None
        sid=False
        if len(ids)>1:
            sid=ids[1]
        oid=ids[0]
        relDatas.append(oid)
        relDatas.append(self._implodebom(cr, uid, self._getinbom(cr, uid, oid, sid)))
        prtDatas=self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def GetExplodedBom(self, cr, uid, ids, level=0, currlevel=0):
        """
            Return a list of all children in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        self._packed=[]
        result=[]
        if level==0 and currlevel>1:
            return result
        bomids=self.browse(cr, uid, ids)
        for bomid in bomids:
            for bom in bomid.bom_line_ids:
                children=self.GetExplodedBom(cr, uid, [bom.id], level, currlevel+1)
                result.extend(children)
            if len(str(bomid.bom_id))>0:
                result.append(bomid.id)
        return result

    def SaveStructure(self, cr, uid, relations, level=0, currlevel=0):
        """
            Save EBom relations
        """
        def cleanStructure(parentID=None,sourceID=None):
            """
                Clean relations having sourceID
            """
            if parentID==None or sourceID==None:
                return None
            objPart=self.pool.get('product.product').browse(cr,uid,parentID,context=None)
            ids=self.search(cr,uid,[('product_id','=',objPart.id),('source_id','=',sourceID)])
            self.unlink(cr,uid,ids)                                     # Cleans mrp.bom
            ids=self.search(cr,uid,[('product_tmpl_id','=',objPart.product_tmpl_id.id),('source_id','=',sourceID)])
            self.unlink(cr,uid,ids)                                     # Cleans mrp.bom
            bomLType=self.pool.get('mrp.bom.line')
            ids=bomLType.search(cr,uid,[('bom_id','=',parentID),('source_id','=',sourceID)])
            bomLType.unlink(cr,uid,ids)                                 # Cleans mrp.bom.line


        def toCleanRelations(relations):
            """
                Processes relations  
            """
            listedSource=[]
            for parentName, parentID, tmpChildName, tmpChildID, sourceID, tempRelArgs in relations:
                if (not(sourceID==None)) and (not(sourceID in listedSource)):
                    cleanStructure(parentID,sourceID)
                    listedSource.append(sourceID)
            return False

        def toCompute(parentName, relations):
            """
                Processes relations  
            """
            sourceIDParent=None
            sourceID=None
            bomID=False
            subRelations=[(a, b, c, d, e, f) for a, b, c, d, e, f in relations if a == parentName]
            if len(subRelations)<1: # no relation to save 
                return None
            parentName, parentID, tmpChildName, tmpChildID, sourceID, tempRelArgs=subRelations[0]
            ids=self.search(cr,uid,[('product_id','=',parentID),('source_id','=',sourceID)])
            if not ids:
                bomID=saveParent(parentName, parentID, sourceID, kindBom='ebom')
                for rel in subRelations:
                    #print "Save Relation ", rel
                    parentName, parentID, childName, childID, sourceID, relArgs=rel
                    if parentName == childName:
                        logging.error('toCompute : Father (%s) refers to himself' %(str(parentName)))
                        raise Exception(_('saveChild.toCompute : Father "%s" refers to himself' %(str(parentName))))
    
                    tmpBomId=saveChild(childName, childID, sourceID, bomID, kindBom='ebom', args=relArgs)
                    tmpBomId=toCompute(childName, relations)
                self.RebaseProductWeight(cr, uid, bomID, self.RebaseBomWeight(cr, uid, bomID))
            return bomID

        def saveParent(name,  partID, sourceID, kindBom=None, args=None):
            """
                Saves the relation ( parent side in mrp.bom )
            """
            try:
                res={}
                if kindBom!=None:
                    res['type']=kindBom
                else:
                    res['type']='ebom'
                
                objPart=self.pool.get('product.product').browse(cr,uid,partID,context=None)
                res['product_tmpl_id']=objPart.product_tmpl_id.id
                res['product_id']=partID
                res['source_id']=sourceID
                res['name']=name
                if args!=None:
                    for arg in args:
                        res[str(arg)]=args[str(arg)]
                if ('product_qty' in res):
                    if(type(res['product_qty'])!=types.FloatType) or (res['product_qty']<1e-6):
                        res['product_qty']=1.0
                return self.create(cr, uid, res)
            except:
                logging.error("saveParent :  unable to create a relation for part (%s) with source (%d) : %s." %(name,sourceID,str(args)))
                raise AttributeError(_("saveParent :  unable to create a relation for part (%s) with source (%d) : %s." %(name,sourceID,str(sys.exc_info()))))

        def saveChild(name,  partID, sourceID, bomID=None, kindBom=None, args=None):
            """
                Saves the relation ( child side in mrp.bom.line )
            """
            try:
                res={}
                if bomID!=None:
                    res['bom_id']=bomID
                if kindBom!=None:
                    res['type']=kindBom
                else:
                    res['type']='ebom'
                res['product_id']=partID
                res['source_id']=sourceID
                res['name']=name
                if args!=None:
                    for arg in args:
                        res[str(arg)]=args[str(arg)]
                if ('product_qty' in res):
                    if(type(res['product_qty'])!=types.FloatType) or (res['product_qty']<1e-6):
                        res['product_qty']=1.0
                return self.pool.get('mrp.bom.line').create(cr, uid, res)
            except:
                logging.error("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." %(name,sourceID,str(args)))
                raise AttributeError(_("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." %(name,sourceID,str(sys.exc_info()))))

        if len(relations)<1: # no relation to save 
            return False
        parentName, parentID, childName, childID, sourceID, relArgs=relations[0]
        toCleanRelations(relations)
        tmpBomId=toCompute(parentName, relations)
        return False
    
    def _sumBomWeight(self, bomObj):
        """
            Evaluates net weight for assembly, based on BoM object
        """
        weight=0.0
        for bom_line in bomObj.bom_line_ids:
            weight+=(bom_line.product_qty * bom_line.product_id.product_tmpl_id.weight)
        return weight

    def RebaseWeight(self, cr, uid, parentID, sourceID=False, context=None):
        """
            Evaluates net weight for assembly, based on product ID
        """
        weight=0.0
        values={}
        if not(parentID==None) or parentID:
            objPart=self.pool.get('product.product').browse(cr,uid,parentID,context=None)
            for bomID in self._getbom(cr, uid, objPart.product_tmpl_id.id, sourceID):
                weight=self._sumBomWeight(bomID)
                values['weight']=weight
                partType=self.pool.get(bomID.product_tmpl_id._inherit)
                partType.write(cr,uid,[bomID.product_tmpl_id.id],values)
        return weight

    def RebaseProductWeight(self, cr, uid, parentBomID, weight=0.0):
        """
            Evaluates net weight for assembly, based on product ID
        """
        if not(parentBomID==None) or parentBomID:
            bomObj=self.browse(cr,uid,parentBomID,context=None)
            self.pool.get('product.product').write(cr,uid,[bomObj.product_id.id],{'weight': weight})

    def RebaseBomWeight(self, cr, uid, bomID, context=None):
        """
            Evaluates net weight for assembly, based on BoM ID
        """
        weight=0.0
        if  bomID:
            for bomId in self.browse(cr, uid, bomID, context):
                weight=self._sumBomWeight(bomId)
                super(plm_relation,self).write(cr, uid, [bomId.id], {'weight_net': weight}, context=context)
        return weight


#   Overridden methods for this entity
    def write(self, cr, uid, ids, vals, check=True, context=None):
        ret=super(plm_relation,self).write(cr, uid, ids, vals, context=context)
        for bomId in self.browse(cr,uid,ids,context=None):
            self.RebaseBomWeight(cr, uid, bomId.id, context=context)
        return ret

    def copy(self,cr,uid,oid,defaults={},context=None):
        """
            Return new object copied (removing SourceID)
        """
        newId=super(plm_relation,self).copy(cr,uid,oid,defaults,context=context)
        if newId:
            compType=self.pool.get('product.product')
            bomLType=self.pool.get('mrp.bom.line')
            newOid=self.browse(cr,uid,newId,context=context)
            for bom_line in newOid.bom_line_ids:
                lateRevIdC=compType.GetLatestIds(cr,uid,[(bom_line.product_id.product_tmpl_id.engineering_code,False,False)],context=context) # Get Latest revision of each Part
                bomLType.write(cr,uid,[bom_line.id],{'source_id':False,'name':bom_line.product_id.product_tmpl_id.name,'product_id':lateRevIdC[0]},context=context)
            self.write(cr,uid,[newId],{'source_id':False,'name':newOid.product_tmpl_id.name,},check=False,context=context)
        return newId

#   Overridden methods for this entity

plm_relation()

class plm_material(models.Model):
    _name = "plm.material"
    _description = "PLM Materials"

    name            =   fields.Char(_('Designation'), size=128, required=True)
    description     =   fields.Char(_('Description'), size=128)
    sequence        =   fields.Integer(_('Sequence'), help=_("Gives the sequence order when displaying a list of product categories."))

#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', _('Raw Material has to be unique !')),
    ]
plm_material()

class plm_finishing(models.Model):
    _name = "plm.finishing"
    _description = "Surface Finishing"

    name            =   fields.Char(_('Specification'), size=128, required=True)
    description     =   fields.Char(_('Description'), size=128)
    sequence        =   fields.Integer(_('Sequence'), help=_("Gives the sequence order when displaying a list of product categories."))

#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.finishing'),
#    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', _('Raw Material has to be unique !')),
    ]
plm_finishing()


class plm_temporary(osv.osv.osv_memory):
    _name = "plm.temporary"
    _description = "Temporary Class"

    name    =   fields.Char(_('Temp'), size=128)


    def action_create_normalBom(self, cr, uid, ids, context=None):
        """
            Create a new Spare Bom if doesn't exist (action callable from views)
        """
        if not 'active_id' in context:
            return False
        if not 'active_ids' in context:
            return False
        
        productType=self.pool.get('product.product')
        for idd in context['active_ids']:
            checkObj=productType.browse(cr, uid, idd, context)
            if not checkObj:
                continue
            objBoms=self.pool.get('mrp.bom').search(cr, uid, [('product_tmpl_id','=',idd),('type','=','normal')])
            if objBoms:
                raise osv.except_osv(_('Creating a new Normal Bom Error.'), _("BoM for Part %r already exists." %(checkObj.name)))

        productType.action_create_normalBom_WF(cr, uid, context['active_ids'])

        return {
              'name': _('Bill of Materials'),
              'view_type': 'form',
              "view_mode": 'tree,form',
              'res_model': 'mrp.bom',
              'type': 'ir.actions.act_window',
              'domain': "[('product_id','in', ["+','.join(map(str,context['active_ids']))+"])]",
         }

    
plm_temporary()
