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
from osv import osv, fields
from tools.translate import _
import logging


# To be adequated to plm.document class states
USED_STATES=[('draft','Draft'),('confirmed','Confirmed'),('transmitted','Transmitted'),('released','Released'),('undermodify','UnderModify'),('obsoleted','Obsoleted'),('reactivated','Reactivated')]

class plm_component(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'
    _columns = {
                'state':fields.selection(USED_STATES,'Status',readonly="True"),
                'engineering_code': fields.char('Part Number',size=64),
                'engineering_revision': fields.integer('Revision', required=True),
                'engineering_writable': fields.boolean('Writable'),
                'engineering_material': fields.char('Raw Material',size=128,required=False,help="Raw material for current product"),
#                'engineering_treatment': fields.char('Treatment',size=64,required=False,help="Thermal treatment for current product"),
                'engineering_surface': fields.char('Surface Finishing',size=128,required=False,help="Surface finishing for current product"),
     }   
    _defaults = {
                 'state': lambda *a: 'draft',
                 'engineering_revision': lambda self,cr,uid,ctx:0,
                 'engineering_writable': lambda *a: True,
                 'type': 'product',
                 'supply_method': 'produce',
                 'procure_method':'make_to_order',
                 'categ_id': 1,
                 'standard_price': 0,
                 'volume':0,
                 'weight_net':0,
                 'cost_method':0,
                 'sale_ok':0,
                 'purchase_ok':0,
                 'state':'draft',
                 'uom_id':1,
                 'uom_po_id':1,
                 'mes_type':'fixed',
                 'cost_method':'standard',
    }
    _sql_constraints = [
        ('partnumber_uniq', 'unique (engineering_code,engineering_revision)', 'Part Number has to be unique!')
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

class plm_component_document_rel(osv.osv):
    _name = 'plm.component.document.rel'
    _description = "Component Document Relations"
    _columns = {
                'component_id': fields.integer('Component Linked', required=True),
                'document_id': fields.integer('Document Linked', required=True),
    }

    _sql_constraints = [
        ('relation_unique', 'unique(component_id,document_id)', 'Component and Document relation has to be unique !'),
    ]

    def SaveStructure(self, cr, uid, relations, level=0, currlevel=0):
        """
            Save Document relations
        """
        def cleanStructure(relations):
            res={}
            latest=None
            for relation in relations:
                res['document_id'],res['component_id']=relation
                if latest==res['document_id']:
                    continue
                latest=res['document_id']
                ids=self.search(cr,uid,[('document_id','=',res['document_id']),('component_id','=',res['component_id'])])
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
                raise Exception("saveChild: Unable to create a link.")
            
        if len(relations)<1: # no relation to save 
            return False
        cleanStructure(relations)
        for relation in relations:
            saveChild(relation)
        return False

plm_component_document_rel()

         
class plm_relation(osv.osv):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'
    _columns = {
                'create_date': fields.datetime('Date Created', readonly=True),
                'source_id': fields.many2one('plm.document','name',ondelete='no action', readonly=True,help="This is the document object that declares this BoM."),
                'type': fields.selection([('normal','Normal BoM'),('phantom','Sets / Phantom'),('ebom','Engineering BoM'),('spbom','Spare BoM')], 'BoM Type', required=True, help=
                    "Use a phantom bill of material in raw materials lines that have to be " \
                    "automatically computed in on eproduction order and not one per level." \
                    "If you put \"Phantom/Set\" at the root level of a bill of material " \
                    "it is considered as a set or pack: the products are replaced by the components " \
                    "between the sale order to the picking without going through the production order." \
                    "The normal BoM will generate one production order per BoM level."),
                'itemnum': fields.integer(_('Cad Item Position')),
                'itemlbl': fields.char(_('Cad Item Position Label'),size=64)
                }
    _defaults = {
        'product_uom' : 1,
    }

    def init(self, cr):
        self._packed=[]

    def _getinbomidnullsrc(self, cr, uid, pid):
        counted=[]
        ids=self.search(cr,uid,[('product_id','=',pid),('bom_id','!=',False),('source_id','!=',False),('type','=','ebom')])
        if not ids:
            ids=self.search(cr,uid,[('product_id','=',pid),('bom_id','!=',False),('source_id','!=',False),('type','=','normal')])
        for obj in self.browse(cr,uid,ids,context=None):
            if obj.bom_id in counted:
                continue
            counted.append(obj.bom_id)
        return counted

    def _getinbom(self, cr, uid, pid, sid):
        ids=self.search(cr,uid,[('product_id','=',pid),('bom_id','!=',False),('source_id','=',sid),('type','=','ebom')])
        if not ids:
            ids=self.search(cr,uid,[('product_id','=',pid),('bom_id','!=',False),('source_id','=',sid),('type','=','normal')])
        return self.browse(cr,uid,ids,context=None)

    def _getbomidnullsrc(self, cr, uid, pid):
        counted=[]
        ids=self.search(cr,uid,[('product_id','=',pid),('bom_id','=',False),('source_id','!=',False),('type','=','ebom')])
        if not ids:
            ids=self.search(cr,uid,[('product_id','=',pid),('bom_id','=',False),('source_id','!=',False),('type','=','normal')])
        for obj in self.browse(cr,uid,list(set(ids)),context=None):
            counted.append(obj)
        return list(set(counted))

    def _getbomid(self, cr, uid, pid, sid):
        ids=self._getidbom(cr, uid, pid, sid)
        return self.browse(cr,uid,list(set(ids)),context=None)

    def _getidbom(self, cr, uid, pid, sid):
        ids=self.search(cr,uid,[('product_id','=',pid),('bom_id','=',False),('source_id','=',sid),('type','=','ebom')])
        if not ids:
            ids=self.search(cr,uid,[('product_id','=',pid),('bom_id','=',False),('source_id','=',sid),('type','=','normal')])
        return list(set(ids))

    def _getpackdatas(self, cr, uid, relDatas):
        prtDatas={}
        tmpbuf=(((str(relDatas).replace('[','')).replace(']','')).replace('(','')).replace(')','').split(',')
        tmpids=[int(tmp) for tmp in tmpbuf if len(tmp.strip()) > 0]
        if len(tmpids)<1:
            return prtDatas
        compType=self.pool.get('product.product')
        tmpDatas=compType.read(cr, uid, tmpids)
        for tmpData in tmpDatas:
            prtDatas[str(tmpData['id'])]=tmpData
        return prtDatas

    def _getpackreldatas(self, cr, uid, relDatas, prtDatas):
        relids={}
        relationDatas={}
        bufDatas={}
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
        tmpDatas=setobj.read(cr, uid, relids.values())
        for tmpData in tmpDatas:
            bufDatas[tmpData['id']]=tmpData

        for keyData in relids.keys():
            relationDatas[keyData]=bufDatas[relids[keyData]]
        return relationDatas

    def _bomid(self, cr, uid, pid, sid=None):
        if sid == None:
            return self._getbomidnullsrc(cr, uid, pid)
        else:
            return self._getbomid(cr, uid, pid, sid)

    def _inbomid(self, cr, uid, pid, sid=None):
        if sid == None:
            return self._getinbomidnullsrc(cr, uid, pid)
        else:
            return self._getinbom(cr, uid, pid, sid)

    def GetWhereUsed(self, cr, uid, ids, context=None):
        """
            Return a list of all fathers of a Part (all levels)
        """
        self._packed=[]
        relDatas=[]
        sid=None
        if len(ids)<1:
            return None
        
        if len(ids)>1:
            sid=ids[1]
        oid=ids[0]
        relDatas.append(oid)
        relDatas.append(self._implodebom(cr, uid, self._inbomid(cr, uid, oid, sid)))
        prtDatas=self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))
    
    def GetExplose(self, cr, uid, ids, context=None):
        """
            Return a list of all children in a Bom (all levels)
        """
        self._packed=[]
        relDatas=[ids[0],self._explodebom(cr, uid, self._bomid(cr, uid, ids[0]), False)]
        prtDatas=self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def _explodebom(self, cr, uid, bids, check=True):
        """
            Explodes a bom entity  (all levels)
        """
        output=[]
        for bid in bids:
            for bom_line in bid.bom_lines:
                if check and (bom_line.product_id.id in self._packed):
                    continue
                innerids=self._explodebom(cr, uid, self._bomid(cr, uid, bom_line.product_id.id), check)
                self._packed.append(bom_line.product_id.id)
                output.append([bom_line.product_id.id, innerids])
        return(output)
    

    def GetExploseSum(self, cr, uid, ids, context=None):
        """
            Return a list of all children in a Bom taken once (all levels)
        """
        self._packed=[]
        relDatas=[ids[0],self._explodebom(cr, uid, self._bomid(cr, uid, ids[0]), True)]
        prtDatas=self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def _implodebom(self, cr, uid, bomObjs):
        """
            Execute implosion for a a bom object
        """
        pids=[]
        for bomObj in bomObjs:
            if not bomObj.product_id:
                continue
            if bomObj.product_id.id in self._packed:
                continue
            self._packed.append(bomObj.product_id.id)
            innerids=self._implodebom(cr, uid, self._inbomid(cr, uid, bomObj.product_id.id))
            pids.append((bomObj.product_id.id,innerids))
        return (pids)

    def GetWhereUsedSum(self, cr, uid, ids, context=None):
        """
            Return a list of all fathers of a Part (all levels)
        """
        self._packed=[]
        relDatas=[]
        sid=None
        if len(ids)<1:
            return None
        
        if len(ids)>1:
            sid=ids[1]
        oid=ids[0]
        relDatas.append(oid)
        relDatas.append(self._implodebom(cr, uid, self._inbomid(cr, uid, oid, sid)))
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
            for bom in bomid.bom_lines:
                children=self.GetExplodedBom(cr, uid, [bom.id], level, currlevel+1)
                result.extend(children)
            if len(str(bomid.bom_id))>0:
                result.append(bomid.id)
        return result

    def SaveStructure(self, cr, uid, relations, level=0, currlevel=0):
        """
            Save EBom relations
        """
        def cleanStructure(sourceID=None):
            """
                Clean relations having sourceID
            """
            if sourceID==None:
                return None
            ids=self.search(cr,uid,[('source_id','=',sourceID)])
            self.unlink(cr,uid,ids)

        def toCleanRelations(parentName, relations):
            """
                Processes relations  
            """
            listedChildren=[]
            sourceID=None
            subRelations=[(a, b, c, d, e, f) for a, b, c, d, e, f in relations if a == parentName]
            if len(subRelations)<1: # no relation to save 
                return None
            parentName, parentID, tmpChildName, tmpChildID, sourceID, tempRelArgs=subRelations[0]
            relids=self._getidbom(cr, uid, parentID, sourceID)
            self.unlink(cr,uid,relids)
            for rel in subRelations:
                #print "Save Relation ", rel
                parentName, parentID, childName, childID, sourceID, relArgs=rel
                if parentName == childName:
                    logging.error('toCleanRelations : Father %s refers to himself' %(str(parentName)))
                    continue
                if not (childName in listedChildren):
                    toCleanRelations(childName, relations)
                    listedChildren.append(childName)
            return False

        def toCompute(parentName, relations):
            """
                Processes relations  
            """
            sourceID=None
            subRelations=[(a, b, c, d, e, f) for a, b, c, d, e, f in relations if a == parentName]
            if len(subRelations)<1: # no relation to save 
                return None
            parentName, parentID, tmpChildName, tmpChildID, sourceID, tempRelArgs=subRelations[0]
            bomID=saveChild(parentName, parentID, sourceID, kindBom='ebom')
            for rel in subRelations:
                #print "Save Relation ", rel
                parentName, parentID, childName, childID, sourceID, relArgs=rel
                if parentName == childName:
                    logging.error('toCompute : Father (%s) refers to himself' %(str(parentName)))
                    raise Exception('saveChild.toCompute : Father "%s" refers to himself' %(str(parentName)))

                tmpBomId=saveChild(childName, childID, sourceID, bomID, kindBom='ebom', args=relArgs)
                tmpBomId=toCompute(childName, relations)
            return bomID

        def saveChild(name,  partID, sourceID, bomID=None, kindBom=None, args=None):
            """
                save the relation 
            """
            try:
                res={}
                if bomID!=None:
                    res['bom_id']=bomID
                if kindBom!=None:
                    res['type']=kindBom
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
                logging.error("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." %(name,sourceID,str(args)))
                raise AttributeError(_("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." %(name,sourceID,str(sys.exc_info()))))

        if len(relations)<1: # no relation to save 
            return False
        parentName, parentID, childName, childID, sourceID, relArgs=relations[0]
        toCleanRelations(parentName, relations)
        tmpBomId=toCompute(parentName, relations)
        weight=self.RebaseWeight(cr, uid, self.browse(cr,uid,tmpBomId).child_complete_ids)
        return False
    
    def RebaseWeight(self, cr, uid, bomObjects, context=None):
        """
            Evaluate net weight for assembly, based on net weight of each part  
        """
        weight=0.0
        values={}
        ancestor=None
        for obj in bomObjects:
            ancestor=obj.bom_id.product_id
            if obj.child_complete_ids:
                weight+=self.RebaseWeight(cr, uid, obj.child_complete_ids)
            else:
                weight+=(obj.product_qty * obj.product_id.weight_net)
        if (ancestor!=None):
            values['weight_net']=weight
            partType=self.pool.get(ancestor._table_name)
            partType.write(cr,uid,[ancestor.id],values,check=False)
        return weight

#   Overridden methods for this entity
    def copy(self,cr,uid,oid,defaults={},context=None):
        """
            Return new object copied (removing SourceID)
        """
        compType=self.pool.get('product.product')
        newId=super(plm_relation,self).copy(cr,uid,oid,defaults,context=context)
        if newId:
            newOid=self.browse(cr,uid,newId,context=context)
            for bom_line in newOid.bom_lines:
                lateRevIdC=compType.GetLatestIds(cr,uid,[(bom_line.product_id.engineering_code,False,False)],context=context) # Get Latest revision of each Part
                self.write(cr,uid,[bom_line.id],{'source_id':False,'name':bom_line.name.replace(' Copy',''),'product_id':lateRevIdC[0]},context=None)
            self.write(cr,uid,[newId],{'source_id':False,},context=None)
        return newId

    def _check_product(self, cr, uid, ids, context=None):
        """
            Override original one, to allow to have multiple lines with same Part Number
        """
        return True
    _constraints = [
        (_check_product, 'BoM line product should not be same as BoM product.', ['product_id']),
    ]
#   Overridden methods for this entity

plm_relation()

class plm_material(osv.osv):
    _name = "plm.material"
    _description = "PLM Materials"
    _columns = {
                'name': fields.char('Designation', size=128, required=True, translate=True),
                'description': fields.char('Description', size=128, translate=True),
                'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of product categories."),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Raw Material has to be unique !'),
    ]
plm_material()

class plm_finishing(osv.osv):
    _name = "plm.finishing"
    _description = "Surface Finishing"
    _columns = {
                'name': fields.char('Specification', size=128, required=True, translate=True),
                'description': fields.char('Description', size=128, translate=True),
                'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of product categories."),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.finishing'),
#    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Raw Material has to be unique !'),
    ]
plm_finishing()


class plm_temporary(osv.osv_memory):
    _name = "plm.temporary"
    _description = "Temporary Class"
    _columns = {
                'name': fields.char('Temp', size=128),
    }

    def action_create_normalBom(self, cr, uid, ids, context=None):
        """
            Create a new Spare Bom if doesn't exist (action callable from views)
        """
        if not 'active_id' in context:
            return False
        self.pool.get('product.product').action_create_normalBom_WF(cr, uid, context['active_ids'])

        return {
              'name': _('Bill of Materials'),
              'view_type': 'form',
              "view_mode": 'tree,form',
              'res_model': 'mrp.bom',
              'type': 'ir.actions.act_window',
              'domain': "[('product_id','in', ["+','.join(map(str,context['active_ids']))+"])]",
         }

    
plm_temporary()
