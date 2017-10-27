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
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import sys


class MrpBomExtension(models.Model):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

#  ######################################################################################################################################33

#   Overridden methods for this entity

    # TODO: Da rivedere a causa del cambiamento in odoo
    @api.model
    def _bom_find(self, product_tmpl=None, product=None, picking_type=None, company_id=False):
        """ Finds BoM for particular product and product uom.
        @param product_tmpl_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        objBom = super(MrpBomExtension, self)._bom_find(product_tmpl=product_tmpl,
                                                        product=product,
                                                        picking_type=picking_type,
                                                        company_id=company_id)
        if objBom:
            odooPLMBom = ['ebom', 'spbom']
            if objBom.type in odooPLMBom:
                bomBrwsList = self.search([('product_id', '=', objBom.product_id.id),
                                           ('product_tmpl_id', '=', objBom.product_tmpl_id.id),
                                           ('type', 'not in', odooPLMBom)])
                for bomBrws in bomBrwsList:
                    return bomBrws
        return objBom

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
                bom_children_lines = bom_line_objType.search([('product_id', '=', bom_obj.product_id.id)])
            else:
                bom_children_lines = bom_line_objType.search([('product_id', '=', bom_obj.product_id.id),
                                                              ('type', '=', bom_type)])
            for bomLineBrws in bom_children_lines:
                if bomLineBrws.bom_id.id:
                    if not(bomLineBrws.bom_id.id in result):
                        result.extend([bomLineBrws.bom_id.id])
            bom_obj.father_complete_ids = self.env['mrp.bom'].browse(list(set(result)))

    state = fields.Selection(related="product_tmpl_id.state",
                             string=_("Status"),
                             help=_("The status of the product in its LifeCycle."),
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
                             ('phantom', _('Sets / Phantom'))],
                            _('BoM Type'),
                            required=True,
                            help=_("Phantom BOM: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product."
                                   "Ship this product as a set of components (kit)."))
    weight_net = fields.Float('Weight',
                              digits=dp.get_precision(_('Stock Weight')),
                              help=_("The BoM net weight in Kg."),
                              default=0.0)

    engineering_revision = fields.Integer(related="product_tmpl_id.engineering_revision",
                                          string=_("Revision"),
                                          help=_("The revision of the product."),
                                          store=False)

    @api.model
    def init(self):
        self._packed = []

    @api.model
    def _getinbom(self, pid, sid=False):
        bomLType = self.env['mrp.bom.line']
        bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
        if not bomLineBrwsList:
            bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')])
            if not bomLineBrwsList:
                bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('type', '=', 'normal')])
        return bomLineBrwsList

    @api.model
    def _getbom(self, pid, sid=False):
        if sid is None:
            sid = False
        bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
        if not bomBrwsList:
            bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')])
            if not bomBrwsList:
                bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('type', '=', 'normal')])
        return bomBrwsList

    def getListIdsFromStructure(self, structure):
        '''
            Convert from [id1,[[id2,[]]]] to [id1,id2]
        '''
        outList = []
        if isinstance(structure, (list, tuple)) and len(structure) == 2:
            if structure[0]:
                outList.append(structure[0])
            for item in structure[1]:
                outList.extend(self.getListIdsFromStructure(item))
        return list(set(outList))

    @api.model
    def _getpackdatas(self, relDatas):
        prtDatas = {}
        tmpids = self.getListIdsFromStructure(relDatas)
        if len(tmpids) < 1:
            return prtDatas
        compType = self.env['product.product']
        tmpDatas = compType.browse(tmpids).read()
        for tmpData in tmpDatas:
            for keyData in tmpData.keys():
                if tmpData[keyData] is None:
                    del tmpData[keyData]
            prtDatas[str(tmpData['id'])] = tmpData
        return prtDatas

    @api.model
    def _getpackreldatas(self, relDatas, prtDatas):
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
            relationDatas[keyData] = self.browse(relids[keyData]).read()[0]
        return relationDatas

    @api.model
    def GetWhereUsed(self, resIds):
        """
            Return a list of all fathers of a Part (all levels)
        """
        self._packed = []
        relDatas = []
        if len(resIds) < 1:
            return None
        sid = False
        if len(resIds) > 1:
            sid = resIds[1]
        oid = resIds[0]
        relDatas.append(oid)
        relDatas.append(self._implodebom(self._getinbom(oid, sid)))
        prtDatas = self._getpackdatas(relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(relDatas, prtDatas))

    @api.model
    def GetExplose(self, values=[]):
        """
            Returns a list of all children in a Bom (all levels)
        """
        self._packed = []
        objId, _sourceID, lastRev = values
        # get all ids of the children product in structured way like [[id,childids]]
        relDatas = [objId, self._explodebom(self._getbom(objId), False, lastRev)]
        prtDatas = self._getpackdatas(relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(relDatas, prtDatas))

    @api.model
    def _explodebom(self, bids, check=True, lastRev=False):
        """
            Explodes a bom entity  ( check=False : all levels, check=True : one level )
        """
        output = []
        _packed = []
        for bid in bids:
            for bom_line in bid.bom_line_ids:
                if check and (bom_line.product_id.id in _packed):
                    continue
                tmpl_id = bom_line.product_id.product_tmpl_id.id
                prod_id = bom_line.product_id.id
                if lastRev:
                    newerCompBrws = self.getLastCompId(prod_id)
                    if newerCompBrws:
                        prod_id = newerCompBrws.id
                        tmpl_id = newerCompBrws.product_tmpl_id.id
                innerids = self._explodebom(self._getbom(tmpl_id), check)
                _packed.append(prod_id)
                output.append([prod_id, innerids])
        return(output)

    @api.multi
    def getLastCompId(self, compId):
        prodProdObj = self.env['product.product']
        compBrws = prodProdObj.browse(compId)
        if compBrws:
            prodBrwsList = prodProdObj.search([('engineering_code', '=', compBrws.engineering_code)], order='engineering_revision DESC')
            for prodBrws in prodBrwsList:
                return prodBrws
        return False

    @api.model
    def GetTmpltIdFromProductId(self, product_id=False):
        if not product_id:
            return False
        tmplDictList = self.env['product.product'].browse(product_id).read(['product_tmpl_id'])  # tmplDict = {'product_tmpl_id': (tmpl_id, u'name'), 'id': product_product_id}
        for tmplDict in tmplDictList:
            tmplTuple = tmplDict.get('product_tmpl_id', {})
            if len(tmplTuple) == 2:
                return tmplTuple[0]
        return False

    @api.model
    def GetExploseSum(self, values=[]):
        """
            Return a list of all children in a Bom taken once (all levels)
        """
        compId, _source_id, latestFlag = values
        self._packed = []
        prodTmplId = self.GetTmpltIdFromProductId(compId)
        bomId = self._getbom(prodTmplId)
        explosedBomIds = self._explodebom(bomId, True, latestFlag)
        relDatas = [compId, explosedBomIds]
        prtDatas = self._getpackdatas(relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(relDatas, prtDatas))

    @api.model
    def _implodebom(self, bomLineObjs):
        """
            Execute implosion for a a bom object
        """
        def getProductId(bomLocalObj):
            prodId = bomLocalObj.product_id.id
            if not prodId:
                trmplBrws = bomLocalObj.product_tmpl_id
                if trmplBrws:
                    for variantBrws in trmplBrws.product_variant_ids:
                        return variantBrws.id
            return False
            
        pids = []
        for bomLineObj in bomLineObjs:
            if not bomLineObj.bom_id:
                continue
            bomObj = bomLineObj.bom_id
            parentBomId = bomObj.id
            if parentBomId in self._packed:
                continue
            self._packed.append(parentBomId)
            bomFthObj = bomObj.with_context({})
            innerids = self._implodebom(self._getinbom(getProductId(bomFthObj)))
            prodId = bomFthObj.product_id.id
            if not prodId:
                prodBrwsIds = bomFthObj.product_tmpl_id.product_variant_ids
                if len(prodBrwsIds) == 1:
                    prodId = prodBrwsIds[0].id
                else:
                    logging.error('[_implodebom] Unable to compute product ID, more than one product found: %r' % (prodBrwsIds))
            pids.append((prodId, innerids))
        return (pids)

    @api.model
    def GetWhereUsedSum(self, resIds):
        """
            Return a list of all fathers of a Part (all levels)
        """
        self._packed = []
        relDatas = []
        if len(resIds) < 1:
            return None
        sid = False
        if len(resIds) > 1:
            sid = resIds[1]
        oid = resIds[0]
        relDatas.append(oid)
        bomLineBrwsList = self._getinbom(oid, sid)
        relDatas.append(self._implodebom(bomLineBrwsList))
        prtDatas = self._getpackdatas(relDatas)
        return (relDatas, prtDatas, self._getpackreldatas(relDatas, prtDatas))

    @api.multi
    def GetExplodedBom(self, level=0, currlevel=0):
        """
            Return a list of all children in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        self._packed = []
        result = []
        if level == 0 and currlevel > 1:
            return result
        for bomid in self:
            for bom in bomid.bom_line_ids:
                children = self.GetExplodedBom([bom.id], level, currlevel + 1)
                result.extend(children)
            if len(str(bomid.bom_id)) > 0:
                result.append(bomid.id)
        return result

    @api.model
    def SaveStructure(self, relations, level=0, currlevel=0, kindBom='normal'):
        """
            Save EBom relations
        """
        t_bom_line = self.env['mrp.bom.line']
        t_product_product = self.env['product.product']
        ECOModuleInstalled = self.env.get('mrp.eco', None)

        def cleanStructure(parentID=None, sourceID=None):
            """
                Clean relations having sourceID
            """
            if parentID is None or sourceID is None:
                return False
            objPart = t_product_product.with_context({}).browse(parentID)
            bomBrwsList = self.search(["|",
                                       ('product_id', '=', parentID),
                                       ('product_tmpl_id', '=', objPart.product_tmpl_id.id),
                                       ('source_id', '=', sourceID)])

            bomBrwsList2 = t_bom_line.search([('bom_id', 'in', bomBrwsList.ids),
                                              ('source_id', '=', sourceID)])
            bomBrwsList.unlink()
            bomBrwsList2.unlink()
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
            existingBoms = self.search([('product_id', '=', parentID),
                                        ('source_id', '=', sourceID),
                                        ('active', '=', True)])
            if existingBoms and ECOModuleInstalled != None:
                newBomBrws = existingBoms[0]
                parentVals = getParentVals(parentName, parentID, sourceID)
                parentVals.update({'bom_line_ids': [(5, 0, 0)]})
                newBomBrws.write(parentVals)
                saveChildrenBoms(subRelations, newBomBrws.id, nexRelation)
                for ecoBrws in self.env['mrp.eco'].search([('bom_id', '=', newBomBrws.id)]):
                    ecoBrws._compute_bom_change_ids()
            elif not existingBoms:
                bomID = saveParent(parentName, parentID, sourceID)
                saveChildrenBoms(subRelations, bomID, nexRelation)
                
                
            return bomID

        def saveChildrenBoms(subRelations, bomID, nexRelation):
            for parentName, _parentID, childName, childID, sourceID, relArgs in subRelations:
                if parentName == childName:
                    logging.error('toCompute : Father (%s) refers to himself' % (str(parentName)))
                    raise Exception(_('saveChild.toCompute : Father "%s" refers to himself' % (str(parentName))))

                saveChild(childName, childID, sourceID, bomID, args=relArgs)
                toCompute(childName, nexRelation)
            self.RebaseProductWeight(bomID, self.browse(bomID).rebaseBomWeight())
            
        def repairQty(value):
            if(not isinstance(value, float) or (value < 1e-6)):
                return 1.0
            return value

        def getParentVals(name, partID, sourceID, args=None):
            """
                Saves the relation ( parent side in mrp.bom )
            """
            res = {}
            res['type'] = kindBom
            objPart = t_product_product.with_context({}).browse(partID)
            res['product_tmpl_id'] = objPart.product_tmpl_id.id
            res['product_id'] = partID
            res['source_id'] = sourceID
            if args is not None:
                for arg in args:
                    res[str(arg)] = args[str(arg)]
            if ('product_qty' in res):
                res['product_qty'] = repairQty(res['product_qty'])
            return res


        def saveParent(name, partID, sourceID, args=None):
            try:
                vals = getParentVals(name, partID, sourceID, args)
                return self.create(vals).id
            except Exception as ex:
                logging.error("saveParent :  unable to create a relation for part (%s) with source (%d) : %s. ex: %r" % (name, sourceID, str(args), ex))
                raise AttributeError(_("saveParent :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(sys.exc_info()))))


        def saveChild(name, partID, sourceID, bomID=None, args=None):
            """
                Saves the relation ( child side in mrp.bom.line )
            """
            try:
                res = {}
                if bomID is not None:
                    res['bom_id'] = bomID
                res['type'] = kindBom
                res['product_id'] = partID
                res['source_id'] = sourceID
                if args is not None:
                    for arg in args:
                        res[str(arg)] = args[str(arg)]
                if ('product_qty' in res):
                    res['product_qty'] = repairQty(res['product_qty'])
                return t_bom_line.create(res)
            except Exception as ex:
                logging.error(ex)
                logging.error("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(args)))
                raise AttributeError(_("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(sys.exc_info()))))

        if len(relations) < 1:  # no relation to save
            return False
        parentName, _parentID, _childName, _childID, _sourceID, _relArgs = relations[0]
        if ECOModuleInstalled == None:
            toCleanRelations(relations)
        toCompute(parentName, relations)
        return False

    def _sumBomWeight(self, bomObj):
        """
            Evaluates net weight for assembly, based on BoM object
        """
        weight = 0.0
        for bom_line in bomObj.bom_line_ids:
            weight += (bom_line.product_qty * bom_line.product_id.weight)
        return weight

    @api.model
    def RebaseProductWeight(self, parentBomID, weight=0.0):
        """
            Evaluates net weight for assembly, based on product ID
        """
        if not(parentBomID is None) or parentBomID:
            bomObj = self.with_context({}).browse(parentBomID)
            self.env['product.product'].browse([bomObj.product_id.id]).write({'weight': weight})

    @api.multi
    def rebaseBomWeight(self):
        """
            Evaluates net weight for assembly, based on BoM ID
        """
        weight = 0.0
        for bomBrws in self:
            weight = bomBrws._sumBomWeight(bomBrws)
            super(MrpBomExtension, bomBrws).write({'weight_net': weight})
        return weight

    @api.model
    def create(self, vals):
        return super(MrpBomExtension, self).create(vals)

    @api.multi
    def write(self, vals, check=True):
        ret = super(MrpBomExtension, self).write(vals)
        for bomBrws in self:
            bomBrws.rebaseBomWeight()
        return ret

    @api.multi
    def copy(self, default={}):
        """
            Return new object copied (removing SourceID)
        """
        newBomBrws = super(MrpBomExtension, self).copy(default)
        if newBomBrws:
            for bom_line in newBomBrws.bom_line_ids:
                lateRevIdC = self.env['product.product'].GetLatestIds([(bom_line.product_id.product_tmpl_id.engineering_code,
                                                                        False,
                                                                        False)])  # Get Latest revision of each Part
                bom_line.sudo().write({'state': 'draft'})
                bom_line.write({'source_id': False,
                                'name': bom_line.product_id.product_tmpl_id.name,
                                'product_id': lateRevIdC[0]})
            newBomBrws.sudo().write({'source_id': False,
                              'name': newBomBrws.product_tmpl_id.name},
                             check=False)
        return newBomBrws

    @api.one
    def deleteChildRow(self, documentId):
        """
        delete the bom child row
        """
        for bomLine in self.bom_line_ids:
            if bomLine.source_id.id == documentId and bomLine.type == self.type:
                bomLine.unlink()

    @api.model
    def addChildRow(self, childId, sourceDocumentId, relationAttributes, bomType='normal'):
        """
        add children rows
        """
        relationAttributes.update({'bom_id': self.id,
                                   'product_id': childId,
                                   'source_id': sourceDocumentId,
                                   'type': bomType})
        self.bom_line_ids.ids.append(self.env['mrp.bom.line'].create(relationAttributes).id)

    @api.multi      # Don't change me with @api.one or I don't work!!!
    def open_related_bom_lines(self):
        for bomBrws in self:
            def recursion(bomBrwsList):
                outBomLines = []
                for bomBrws in bomBrwsList:
                    lineBrwsList = bomBrws.bom_line_ids
                    outBomLines.extend(lineBrwsList.ids)
                    for lineBrws in lineBrwsList:
                        bomsFound = self.search([('product_tmpl_id', '=', lineBrws.product_id.product_tmpl_id.id),
                                                 ('type', '=', lineBrws.type),
                                                 ('active', '=', True)])
                        bottomLineIds = recursion(bomsFound)
                        outBomLines.extend(bottomLineIds)
                return outBomLines

            bomLineIds = recursion(self)
            return {'name': _('B.O.M. Lines'),
                    'res_model': 'mrp.bom.line',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', bomLineIds)],
                    'context': {"group_by": ['bom_id']},
                    }

MrpBomExtension()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
