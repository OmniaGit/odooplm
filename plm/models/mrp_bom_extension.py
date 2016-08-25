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

'''
Created on 25 Aug 2016

@author: Daniel Smerghetto
'''

import odoo.addons.decimal_precision as dp
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
import logging
import sys


class MrpBomExtension(models.Model):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

#  ######################################################################################################################################33

#   Overridden methods for this entity

    def _bom_find(self, cr, uid, product_tmpl_id=None, product_id=None, properties=None, context=None):
        """ Finds BoM for particular product and product uom.
        @param product_tmpl_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        bom_id = super(MrpBomExtension, self)._bom_find(cr,
                                                     uid,
                                                     product_tmpl_id=product_tmpl_id,
                                                     product_id=product_id,
                                                     properties=properties,
                                                     context=context)
        if bom_id:
            objBom = self.browse(cr, uid, bom_id, context)
            odooPLMBom = ['ebom', 'spbom']
            if objBom.type in odooPLMBom:
                bom_ids = self.search(cr, uid, [('product_id', '=', objBom.product_id.id),
                                                ('product_tmpl_id', '=', objBom.product_tmpl_id.id),
                                                ('type', 'not in', odooPLMBom)])
                for _id in bom_ids:
                    return _id
        return bom_id

#  ######################################################################################################################################33
    @api.multi
    def _father_compute(self, name='', arg={}):
        """ Gets father bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        bom_type = ''
        bom_line_objType = self.env['mrp.bom.line']
        for bom_obj in self:
            result = []
            bom_type = bom_obj.type
            if bom_type == '':
                bom_children = bom_line_objType.search([('product_id', '=', bom_obj.product_id.id)])
            else:
                bom_children = bom_line_objType.search([('product_id', '=', bom_obj.product_id.id),
                                                        ('type', '=', bom_type)])
            for bom_child in bom_children:
                if bom_child.bom_id.id:
                    if not(bom_child.bom_id.id in result):
                        result.extend([bom_child.bom_id.id])
            bom_obj.father_complete_ids = self.env['mrp.bom'].browse(list(set(result)))

    state = fields.Selection(related="product_tmpl_id.state",
                             string=_("Status"),
                             help=_("The status of the product in its LifeCycle."),
                             store=False)
    engineering_revision = fields.Integer(related="product_tmpl_id.engineering_revision",
                                          string=_("Revision"),
                                          help=_("The revision of the product."),
                                          store=False)
    description = fields.Text(related="product_tmpl_id.description",
                              string=_("Description"),
                              store=False)
    father_complete_ids = fields.Many2many('mrp.bom',
                                           compute=_father_compute,
                                           string=_("BoM Hierarchy"),
                                           store=False)
    create_date = fields.Datetime(_('Creation Date'),
                                  readonly=True)
    source_id = fields.Many2one('plm.document',
                                'name',
                                ondelete='no action',
                                readonly=True,
                                help=_('This is the document object that declares this BoM.'))
    type = fields.Selection([('normal', _('Normal BoM')),
                             ('phantom', _('Sets / Phantom')),
                             ('ebom', _('Engineering BoM')),
                             ('spbom', _('Spare BoM'))],
                            _('BoM Type'),
                            required=True,
                            help=_("Phantom BOM: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product."
                                   "Ship this product as a set of components (kit)."))
    weight_net = fields.Float('Weight',
                              digits_compute=dp.get_precision(_('Stock Weight')),
                              help=_("The BoM net weight in Kg."))
    ebom_source_id = fields.Integer('Source Ebom ID')

    _defaults = {
        'product_uom_id': 1,
        'weight_net': 0.0,
    }

    def init(self, cr):
        self._packed = []

    def _getinbom(self, cr, uid, pid, sid=False):
        bomLType = self.pool.get('mrp.bom.line')
        ids = bomLType.search(cr, uid, [('product_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'ebom')])
        if not ids:
            ids = bomLType.search(cr, uid, [('product_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
            if not ids:
                ids = bomLType.search(cr, uid, [('product_id', '=', pid), ('source_id', '=', False), ('type', '=', 'ebom')])
            if not ids:
                ids = bomLType.search(cr, uid, [('product_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')])
                if not ids:
                    ids = bomLType.search(cr, uid, [('product_id', '=', pid), ('type', '=', 'ebom')])
                if not ids:
                    ids = bomLType.search(cr, uid, [('product_id', '=', pid), ('type', '=', 'normal')])
        return bomLType.browse(cr, uid, list(set(ids)), context=None)

    def _getbom(self, cr, uid, pid, sid=False):
        if sid is None:
            sid = False
        ids = self.search(cr, uid, [('product_tmpl_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'ebom')])
        if not ids:
            ids = self.search(cr, uid, [('product_tmpl_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
            if not ids:
                ids = self.search(cr, uid, [('product_tmpl_id', '=', pid), ('source_id', '=', False), ('type', '=', 'ebom')])
                if not ids:
                    ids = self.search(cr, uid, [('product_tmpl_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')])
                    if not ids:
                        ids = self.search(cr, uid, [('product_tmpl_id', '=', pid), ('type', '=', 'ebom')])
                        if not ids:
                            ids = self.search(cr, uid, [('product_tmpl_id', '=', pid), ('type', '=', 'normal')])
        return self.browse(cr, uid, list(set(ids)), context=None)

    def getListIdsFromStructure(self, structure):
        '''
            Convert from [id1,[[id2,[]]]] to [id1,id2]
        '''
        outList = []
        if isinstance(structure, (list, tuple)) and len(structure) == 2:
            outList.append(structure[0])
            for item in structure[1]:
                outList.extend(self.getListIdsFromStructure(item))
        return list(set(outList))

    def _getpackdatas(self, cr, uid, relDatas):
        prtDatas = {}
        tmpids = self.getListIdsFromStructure(relDatas)
        if len(tmpids) < 1:
            return prtDatas
        compType = self.pool.get('product.product')
        tmpDatas = compType.read(cr, uid, tmpids)
        for tmpData in tmpDatas:
            for keyData in tmpData.keys():
                if tmpData[keyData] is None:
                    del tmpData[keyData]
            prtDatas[str(tmpData['id'])] = tmpData
        return prtDatas

    def _getpackreldatas(self, cr, uid, relDatas, prtDatas):
        relids = {}
        relationDatas = {}
        tmpids = self.getListIdsFromStructure(relDatas)
        if len(tmpids) < 1:
            return prtDatas
        for keyData in prtDatas.keys():
            tmpData = prtDatas[keyData]
            if len(tmpData['bom_ids']) > 0:
                relids[keyData] = tmpData['bom_ids'][0]

        if len(relids) < 1:
            return relationDatas
        for keyData in relids.keys():
            relationDatas[keyData] = self.read(cr, uid, relids[keyData])
        return relationDatas

    def GetWhereUsed(self, cr, uid, ids, context=None):
        """
            Return a list of all fathers of a Part (all levels)
        """
        self._packed = []
        relDatas = []
        if len(ids) < 1:
            return None
        sid = False
        if len(ids) > 1:
            sid = ids[1]
        oid = ids[0]
        relDatas.append(oid)
        relDatas.append(self._implodebom(cr, uid, self._getinbom(cr, uid, oid, sid)))
        prtDatas = self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def GetExplose(self, cr, uid, ids, context=None):
        """
            Returns a list of all children in a Bom (all levels)
        """
        self._packed = []
        # get all ids of the children product in structured way like [[id,childids]]
        relDatas = [ids[0], self._explodebom(cr, uid, self._getbom(cr, uid, ids[0]), False)]
        prtDatas = self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def _explodebom(self, cr, uid, bids, check=True):
        """
            Explodes a bom entity  ( check=False : all levels, check=True : one level )
        """
        output = []
        self._packed = []
        for bid in bids:
            for bom_line in bid.bom_line_ids:
                if check and (bom_line.product_id.id in self._packed):
                    continue
                innerids = self._explodebom(cr, uid, self._getbom(cr, uid, bom_line.product_id.product_tmpl_id.id), check)
                self._packed.append(bom_line.product_id.id)
                output.append([bom_line.product_id.id, innerids])
        return(output)

    def GetTmpltIdFromProductId(self, cr, uid, product_id=False):
        if not product_id:
            return False
        tmplDict = self.pool.get('product.product').read(cr, uid, product_id, ['product_tmpl_id'])  # tmplDict = {'product_tmpl_id': (tmpl_id, u'name'), 'id': product_product_id}
        tmplTuple = tmplDict.get('product_tmpl_id', {})
        if len(tmplTuple) == 2:
            return tmplTuple[0]
        return False

    def GetExploseSum(self, cr, uid, ids, context=None):
        """
            Return a list of all children in a Bom taken once (all levels)
        """
        self._packed = []
        prodTmplId = self.GetTmpltIdFromProductId(cr, uid, ids[0])
        bomId = self._getbom(cr, uid, prodTmplId)
        explosedBomIds = self._explodebom(cr, uid, bomId, True)
        relDatas = [ids[0], explosedBomIds]
        prtDatas = self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def _implodebom(self, cr, uid, bomObjs):
        """
            Execute implosion for a a bom object
        """
        pids = []
        for bomObj in bomObjs:
            if not bomObj.bom_id:
                continue
            if bomObj.bom_id.id in self._packed:
                continue
            self._packed.append(bomObj.bom_id.id)
            bomFthObj = self.browse(cr, uid, [bomObj.bom_id.id], context=None)
            innerids = self._implodebom(cr, uid, self._getinbom(cr, uid, bomFthObj.product_id.id))
            pids.append((bomFthObj.product_id.id, innerids))
        return (pids)

    def GetWhereUsedSum(self, cr, uid, ids, context=None):
        """
            Return a list of all fathers of a Part (all levels)
        """
        self._packed = []
        relDatas = []
        if len(ids) < 1:
            return None
        sid = False
        if len(ids) > 1:
            sid = ids[1]
        oid = ids[0]
        relDatas.append(oid)
        bomId = self._getinbom(cr, uid, oid, sid)
        relDatas.append(self._implodebom(cr, uid, bomId))
        prtDatas = self._getpackdatas(cr, uid, relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(cr, uid, relDatas, prtDatas))

    def GetExplodedBom(self, cr, uid, ids, level=0, currlevel=0):
        """
            Return a list of all children in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        self._packed = []
        result = []
        if level == 0 and currlevel > 1:
            return result
        bomids = self.browse(cr, uid, ids)
        for bomid in bomids:
            for bom in bomid.bom_line_ids:
                children = self.GetExplodedBom(cr, uid, [bom.id], level, currlevel + 1)
                result.extend(children)
            if len(str(bomid.bom_id)) > 0:
                result.append(bomid.id)
        return result

    def SaveStructure(self, cr, uid, relations, level=0, currlevel=0):
        """
            Save EBom relations
        """
        t_bom_line = self.pool.get('mrp.bom.line')
        t_product_product = self.pool.get('product.product')

        def cleanStructure(parentID=None, sourceID=None):
            """
                Clean relations having sourceID
            """
            if parentID is None or sourceID is None:
                return False
            objPart = t_product_product.browse(cr, uid, parentID, context=None)
            bomIds = self.search(cr, uid, ["|",
                                           ('product_id', '=', parentID),
                                           ('product_tmpl_id', '=', objPart.product_tmpl_id.id),
                                           ('source_id', '=', sourceID)])

            bomLineIds = t_bom_line.search(cr, uid, [('bom_id', 'in', bomIds),
                                                     ('source_id', '=', sourceID)])
            self.unlink(cr, uid, bomIds)
            t_bom_line.unlink(cr, uid, bomLineIds)
            return True

        def toCleanRelations(relations):
            """
                Processes relations
            """
            listedSource = []
            for _parentName, parentID, _ChildName, _ChildID, sourceID, _RelArgs in relations:
                if sourceID not in listedSource and cleanStructure(parentID, sourceID):
                    listedSource.append(sourceID)
            return False

        def toCompute(parentName, relations):
            """
                Processes relations
            """
            bomID = False
            nexRelation = []

            def divedeByParent(element):
                if element[0] == parentName:
                    return True
                nexRelation.append(element)
            subRelations = filter(divedeByParent, relations)
            if len(subRelations) < 1:  # no relation to save
                return
            parentName, parentID, _ChildName, _ChildID, sourceID, _RelArgs = subRelations[0]
            if not self.search(cr, uid, [('product_id', '=', parentID),
                                         ('source_id', '=', sourceID)]):
                bomID = saveParent(parentName, parentID, sourceID, kindBom='ebom')
                for parentName, parentID, childName, childID, sourceID, relArgs in subRelations:
                    if parentName == childName:
                        logging.error('toCompute : Father (%s) refers to himself' % (str(parentName)))
                        raise Exception(_('saveChild.toCompute : Father "%s" refers to himself' % (str(parentName))))

                    saveChild(childName, childID, sourceID, bomID, kindBom='ebom', args=relArgs)
                    toCompute(childName, nexRelation)
                self.RebaseProductWeight(cr, uid, bomID, self.RebaseBomWeight(cr, uid, bomID))
            return bomID

        def repairQty(value):
            if(not isinstance(value, float) or (value < 1e-6)):
                return 1.0
            return value

        def saveParent(name, partID, sourceID, kindBom=None, args=None):
            """
                Saves the relation ( parent side in mrp.bom )
            """
            try:
                res = {}
                if kindBom is not None:
                    res['type'] = kindBom
                else:
                    res['type'] = 'ebom'
                objPart = t_product_product.browse(cr, uid, partID, context=None)
                res['product_tmpl_id'] = objPart.product_tmpl_id.id
                res['product_id'] = partID
                res['source_id'] = sourceID
                if args is not None:
                    for arg in args:
                        res[str(arg)] = args[str(arg)]
                if ('product_qty' in res):
                    res['product_qty'] = repairQty(res['product_qty'])
                return self.create(cr, uid, res)
            except:
                logging.error("saveParent :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(args)))
                raise AttributeError(_("saveParent :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(sys.exc_info()))))

        def saveChild(name, partID, sourceID, bomID=None, kindBom=None, args=None):
            """
                Saves the relation ( child side in mrp.bom.line )
            """
            try:
                res = {}
                if bomID is not None:
                    res['bom_id'] = bomID
                if kindBom is not None:
                    res['type'] = kindBom
                else:
                    res['type'] = 'ebom'
                res['product_id'] = partID
                res['source_id'] = sourceID
                if args is not None:
                    for arg in args:
                        res[str(arg)] = args[str(arg)]
                if ('product_qty' in res):
                    res['product_qty'] = repairQty(res['product_qty'])
                return t_bom_line.create(cr, uid, res)
            except:
                logging.error("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(args)))
                raise AttributeError(_("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(sys.exc_info()))))

        if len(relations) < 1:  # no relation to save
            return False
        parentName, _parentID, _childName, _childID, _sourceID, _relArgs = relations[0]
        toCleanRelations(relations)
        toCompute(parentName, relations)
        return False

    def _sumBomWeight(self, bomObj):
        """
            Evaluates net weight for assembly, based on BoM object
        """
        weight = 0.0
        for bom_line in bomObj.bom_line_ids:
            weight += (bom_line.product_qty * bom_line.product_id.product_tmpl_id.weight)
        return weight

    def RebaseProductWeight(self, cr, uid, parentBomID, weight=0.0):
        """
            Evaluates net weight for assembly, based on product ID
        """
        if not(parentBomID is None) or parentBomID:
            bomObj = self.browse(cr, uid, parentBomID, context=None)
            self.pool.get('product.product').write(cr, uid, [bomObj.product_id.id], {'weight': weight})

    def RebaseBomWeight(self, cr, uid, bomID, context=None):
        """
            Evaluates net weight for assembly, based on BoM ID
        """
        weight = 0.0
        if bomID:
            for bomId in self.browse(cr, uid, bomID, context):
                weight = self._sumBomWeight(bomId)
                super(MrpBomExtension, self).write(cr, uid, [bomId.id], {'weight_net': weight}, context=context)
        return weight


#   Overridden methods for this entity
    def write(self, cr, uid, ids, vals, check=True, context=None):
        ret = super(MrpBomExtension, self).write(cr, uid, ids, vals, context=context)
        for bomId in self.browse(cr, uid, ids, context=None):
            self.RebaseBomWeight(cr, uid, bomId.id, context=context)
        return ret

    def copy(self, cr, uid, oid, defaults={}, context=None):
        """
            Return new object copied (removing SourceID)
        """
        newId = super(MrpBomExtension, self).copy(cr, uid, oid, defaults, context=context)
        if newId:
            compType = self.pool.get('product.product')
            bomLType = self.pool.get('mrp.bom.line')
            newOid = self.browse(cr, uid, newId, context=context)
            for bom_line in newOid.bom_line_ids:
                lateRevIdC = compType.GetLatestIds(cr, uid, [(bom_line.product_id.product_tmpl_id.engineering_code, False, False)], context=context)  # Get Latest revision of each Part
                bomLType.write(cr, uid, [bom_line.id], {'source_id': False, 'name': bom_line.product_id.product_tmpl_id.name, 'product_id': lateRevIdC[0]}, context=context)
            self.write(cr, uid, [newId], {'source_id': False, 'name': newOid.product_tmpl_id.name}, check=False, context=context)
        return newId

MrpBomExtension()
