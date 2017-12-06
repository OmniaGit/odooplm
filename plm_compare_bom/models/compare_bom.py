# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2012 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
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
import logging
from openerp import models, fields, api, SUPERUSER_ID, _, osv
_logger = logging.getLogger(__name__)


def _moduleName():
    path = os.path.dirname(__file__)
    return os.path.basename(os.path.dirname(path))
openerpModule = _moduleName()


def _modulePath():
    return os.path.dirname(__file__)
openerpModulePath = _modulePath()


def _customPath():
    return os.path.join(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'custom'), 'report')
customModulePath = _customPath()

BOM_SHOW_FIELDS = ['Position',
                   'Code',
                   'Description',
                   'Quantity']
# TODO: Remember to adequate views for added/missing entities changing BOM_SHOW_FIELDS.

##############################################################################################################
#    Class plm.compare.bom
###############################################################################################################
class plm_missing_bom(osv.osv.osv_memory):
    _name = "plm.missing.bom"
    _description = "BoM Missing Objects"

    bom_id = fields.Many2one('plm.compare.bom', _('BoM'), ondelete='cascade')
    bom_idrow = fields.Many2one('mrp.bom.line', _('BoM Line'), ondelete='cascade')
    part_id = fields.Many2one('product.product', _('Part'), ondelete='cascade')
    revision = fields.Integer(related="part_id.engineering_revision", string=_("Revision"), store=False)
    description = fields.Text(related="part_id.description", string=_("Description"), store=False)
    itemnum = fields.Integer(related="bom_idrow.itemnum", string=_("Cad Item Position"), store=False)
    itemqty = fields.Float(string=_("Quantity"), digits=(16, 3))
    reason = fields.Char(string=_("Difference"), size=32)

    _defaults = {
    }
plm_missing_bom()


class plm_adding_bom(osv.osv.osv_memory):
    _name = "plm.adding.bom"
    _description = "BoM Adding Objects"

    bom_id = fields.Many2one('plm.compare.bom', _('BoM'), ondelete='cascade')
    bom_idrow = fields.Many2one('mrp.bom.line', _('BoM Line'), ondelete='cascade')
    part_id = fields.Many2one('product.product', _('Part'), ondelete='cascade')
    revision = fields.Integer(related="part_id.engineering_revision", string=_("Revision"), store=False)
    description = fields.Text(related="part_id.description", string=_("Description"), store=False)
    itemnum = fields.Integer(related="bom_idrow.itemnum", string=_("Cad Item Position"), store=False)
    itemqty = fields.Float(string=_("Quantity"), digits=(16, 3))
    reason = fields.Char(string=_("Difference"), size=32)

    _defaults = {
    }
plm_adding_bom()


class plm_compare_bom(osv.osv.osv_memory):
    _name = "plm.compare.bom"
    _description = "BoM Comparison"

    name = fields.Char(_('Part Number'), size=64)
    bom_id1 = fields.Many2one('mrp.bom', _('BoM 1'), required=True, ondelete='cascade')
    type_id1 = fields.Selection([('normal', _('Normal BoM')),
                                 ('phantom', _('Sets / Phantom')),
                                 ('ebom', _('Engineering BoM')),
                                 ('spbom', _('Spare BoM'))],
                                _('BoM Type'))
    part_id1 = fields.Many2one('product.product', 'Part', ondelete='cascade')
    revision1 = fields.Integer(related="part_id1.engineering_revision", string=_("Revision"), store=False)
    description1 = fields.Text(related="part_id1.description", string=_("Description"), store=False)
    bom_id2 = fields.Many2one('mrp.bom', _('BoM 2'), required=True, ondelete='cascade')
    type_id2 = fields.Selection([('normal', _('Normal BoM')),
                                 ('phantom', _('Sets / Phantom')),
                                 ('ebom', _('Engineering BoM')),
                                 ('spbom', _('Spare BoM'))],
                                _('BoM Type'))
    part_id2 = fields.Many2one('product.product', 'Part', ondelete='cascade')
    revision2 = fields.Integer(related="part_id2.engineering_revision", string=_("Revision"), store=False)
    description2 = fields.Text(related="part_id2.description", string=_("Description"), store=False)
    anotinb = fields.One2many('plm.adding.bom', 'bom_id', _('BoM Adding'))
    bnotina = fields.One2many('plm.missing.bom', 'bom_id', _('BoM Missing'))
    
    compute_type = fields.Selection('_get_radio_choice_options',
                                    string=_('Compare type'))

    _defaults = {'name': 'x',
                 'compute_type': 'only_product'}

    @api.multi
    def _get_radio_choice_options(self):
        return [('only_product', _('Compare Only Product Existence')),
                ('num_qty', _('Compare By Item Number and Quantity')),
                ('summarized', _('Compare Product Quantity'))]
        
    @api.model
    def default_get(self, fields):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        record_ids = self.env.context.get('active_ids')
        res = {}
        if len(record_ids) > 0:
            res['bom_id1'] = record_ids[0]
        if len(record_ids) > 1:
            res['bom_id2'] = record_ids[1]
        return res

    def computeBomLines(self, bomBrws):
        bomDict = {}
        for bomLineBrws in bomBrws.bom_line_ids:
            productId = bomLineBrws.product_id.id
            bomLineQty = bomLineBrws.product_qty
            createVals = {'part_id': bomLineBrws.product_id.id,
                          'itemqty': bomLineQty,
                          'itemnum': bomLineBrws.itemnum,
                          'bom_idrow': bomLineBrws.id,
                          'reason': '',
                          'bom_id': self.id,
                          'revision': bomLineBrws.product_id.engineering_revision
                          }
            if productId not in bomDict:
                bomDict[productId] = [createVals]
            else:
                if self.compute_type == 'summarized':
                    bomDict[productId]['itemqty'] = bomDict[productId]['itemqty'] + bomLineQty
                else:
                    bomDict[productId].append(createVals)
        return bomDict

    def getLeftBomObj(self, toCreateVals):
        if 'itemnum' in toCreateVals:
            del toCreateVals['itemnum']
        return self.env['plm.adding.bom'].create(toCreateVals).id

    def getRightBomObj(self, toCreateVals):
        if 'itemnum' in toCreateVals:
            del toCreateVals['itemnum']
        return self.env['plm.missing.bom'].create(toCreateVals).id

    def computeOnlyProduct(self, bom1Dict, bom2Dict):

        def checkAndAdd(leftDict, rightDict, listToAppend, funcToCall):
            for product_id, toCreateValsList in leftDict.items():
                if product_id not in rightDict:
                    for toCreateVals in toCreateValsList:
                        toCreateVals['reason'] = _('Added')
                        listToAppend.append(funcToCall(toCreateVals))
            
        leftItems = []
        rightItems = []
        checkAndAdd(bom1Dict, bom2Dict, leftItems, self.getLeftBomObj)
        checkAndAdd(bom2Dict, bom1Dict, rightItems, self.getRightBomObj)
        return leftItems, rightItems

    def computeSummarized(self, bom1Dict, bom2Dict):

        def checkAndAdd(leftDict, rightDict, listToAppend):
            for product_id, toCreateValsList in leftDict.items():
                for toCreateVals in toCreateValsList: # Always 1 because summarized
                    if product_id not in rightDict:
                        toCreateVals['reason'] = _('Added')
                        listToAppend.append(self.getLeftBomObj(toCreateVals))
                    else:
                        qtyLeftDict = toCreateVals['itemqty']
                        qtyRightDict = rightDict[product_id][0]['itemqty']
                        resQty = qtyLeftDict - qtyRightDict
                        toCreateVals['reason'] = _('Changed Qty')
                        toCreateVals['itemqty'] = abs(resQty)
                        if resQty > 0:
                            leftItems.append(self.getLeftBomObj(toCreateVals))
                        elif resQty < 0:
                            rightItems.append(self.getRightBomObj(toCreateVals))
                        del rightDict[product_id]   # Erase already computed product
                        
        leftItems = []
        rightItems = []
        tmpDict2 = bom2Dict.copy()
        checkAndAdd(bom1Dict, tmpDict2, leftItems)
        # Append lines presents only on right side
        for toCreateValsList in tmpDict2.values():
            toCreateValsList[0]['reason'] = _('Added')
            rightItems.append(self.getRightBomObj(toCreateValsList[0]))
        return leftItems, rightItems
    
    def computeByQty(self, bom1Dict, bom2Dict):

        def checkAndAdd(leftDict, rightDict, listToAppend):
            for product_id, toCreateValsList in leftDict.items():
                if product_id not in rightDict:
                    # Setup new on left side
                    for toCreateVals in toCreateValsList:
                        toCreateVals['reason'] = _('Added')
                        listToAppend.append(self.getLeftBomObj(toCreateVals))
                        del leftDict[product_id]
                else:
                    # Remove equal product elements
                    for toCreateVals in toCreateValsList:
                        qtyLeftDict = toCreateVals['itemqty']
                        itemNumLeftDict = toCreateVals['itemnum']
                        for toCreateValsRight in rightDict[product_id]:
                            qtyRightDict = toCreateValsRight['itemqty']
                            itemNumRightDict = toCreateValsRight['itemnum']
                            if qtyLeftDict == qtyRightDict and itemNumLeftDict == itemNumRightDict:
                                # Found so remove from right list
                                index = rightDict[product_id].index(toCreateValsRight)
                                del rightDict[product_id][index]
                                # Found so remove from right left
                                index = toCreateValsList.index(toCreateVals)
                                del leftDict[product_id][index]

                    # Setup left product elements
                    for toCreateVals in toCreateValsList:
                        toCreateVals['reason'] = _('Changed')
                        leftItems.append(self.getLeftBomObj(toCreateVals))

                    # Setup right product elements
                    for toCreateVals in rightDict[product_id]:
                        toCreateVals['reason'] = _('Changed')
                        rightItems.append(self.getRightBomObj(toCreateVals))
                    del leftDict[product_id]
                    del rightDict[product_id]
                    
        leftItems = []
        rightItems = []
        checkAndAdd(bom1Dict, bom2Dict, leftItems)
        # Evaluate remaining new on right side
        for product_id, toCreateValsList in bom2Dict.items():
            if product_id not in bom1Dict.keys():
                for toCreateVals in toCreateValsList:
                    toCreateVals['reason'] = _('Added')
                    rightItems.append(self.getRightBomObj(toCreateVals))

        return leftItems, rightItems
        
    @api.multi
    def action_compare_Bom(self):
        """
            Compare two BOMs
        """
        bom1Dict = self.computeBomLines(self.bom_id1)
        bom2Dict = self.computeBomLines(self.bom_id2)
        
        if self.compute_type == 'only_product':
            bom1NewItems, bom2NewItems = self.computeOnlyProduct(bom1Dict, bom2Dict)
        elif self.compute_type == 'summarized':
            bom1NewItems, bom2NewItems = self.computeSummarized(bom1Dict, bom2Dict)
        elif self.compute_type == 'num_qty':
            bom1NewItems, bom2NewItems = self.computeByQty(bom1Dict, bom2Dict)
        else:
            logging.warning('Compute type not found!')
        
        self.anotinb = bom1NewItems
        self.bnotina = bom2NewItems

        data_obj = self.env['ir.model.data']
        id3 = data_obj._get_id(openerpModule, 'plm_visualize_diff_form')
        if id3:
            id3 = data_obj.browse(id3).res_id
        return {
            'domain': [],
            'name': _('Differences on BoMs'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'plm.compare.bom',
            'res_id': self.ids[0],
            'views': [(id3, 'form')],
            'type': 'ir.actions.act_window',
        }

plm_compare_bom()
