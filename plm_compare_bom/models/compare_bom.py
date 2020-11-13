# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2012-2019 OmniaSolutions (<http://www.omniasolutions.website>). All Rights Reserved
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
from openerp import models, fields, api, _, osv
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
    revision = fields.Integer(related="part_id.engineering_revision", string=_("Rev."), store=False)
    description = fields.Char(related="part_id.name", string=_("Description"), store=False)
    itemnum = fields.Integer(related="bom_idrow.itemnum", string=_("Cad Pos."), store=False)
    itemqty = fields.Float(string=_("Quantity"), digits=(16, 3))
    reason = fields.Char(string=_("Difference"), size=32)

    @api.multi
    def delete_bom_line(self):
        for plm_missign_bom_id in self:
            plm_missign_bom_id.bom_id.bom_line_id_to_delete = [(6, True, plm_missign_bom_id.bom_idrow.ids)]
            plm_missign_bom_id.unlink()

    @api.multi
    def copy_left_right(self):
        obj_adding_bom = self.env['plm.adding.bom']
        for plm_missign_bom_id in self:
            obj_adding_bom.create({
                'bom_id': plm_missign_bom_id.bom_id.id,
                'bom_idrow': plm_missign_bom_id.bom_idrow.id,
                'part_id': plm_missign_bom_id.part_id.id,
                'revision': plm_missign_bom_id.revision,
                'description': plm_missign_bom_id.description,
                'itemnum': plm_missign_bom_id.itemnum,
                'itemqty': plm_missign_bom_id.itemqty,
                'reason': 'new'})

    @api.multi
    def move_left_left(self):
        for plm_missign_bom_id in self:
            plm_missign_bom_id.copy_left_right()
            plm_missign_bom_id.delete_bom_line()


class plm_adding_bom(osv.osv.osv_memory):
    _name = "plm.adding.bom"
    _description = "BoM Adding Objects"

    bom_id = fields.Many2one('plm.compare.bom', _('BoM'), ondelete='cascade')
    bom_idrow = fields.Many2one('mrp.bom.line', _('BoM Line'), ondelete='cascade')
    part_id = fields.Many2one('product.product', _('Part'), ondelete='cascade')
    revision = fields.Integer(related="part_id.engineering_revision", string=_("Rev."), store=False)
    description = fields.Char(related="part_id.name", string=_("Description"), store=False)
    itemnum = fields.Integer(related="bom_idrow.itemnum", string=_("Cad Pos."), store=False)
    itemqty = fields.Float(string=_("Quantity"), digits=(16, 3))
    reason = fields.Char(string=_("Difference"), size=32)

    @api.multi
    def delete_bom_line(self):
        for plm_missign_bom_id in self:
            plm_missign_bom_id.bom_id.bom_line_id_to_delete = [(6, True, plm_missign_bom_id.bom_idrow.ids)]
            plm_missign_bom_id.unlink()

    @api.multi
    def copy_right_left(self):
        obj_missing_bom = self.env['plm.missing.bom']
        for plm_missign_bom_id in self:
            obj_missing_bom.create({
                'bom_id': plm_missign_bom_id.bom_id.id,
                'bom_idrow': plm_missign_bom_id.bom_idrow.id,
                'part_id': plm_missign_bom_id.part_id.id,
                'revision': plm_missign_bom_id.revision,
                'description': plm_missign_bom_id.description,
                'itemnum': plm_missign_bom_id.itemnum,
                'itemqty': plm_missign_bom_id.itemqty,
                'reason': 'new'})

    @api.multi
    def move_right_left(self):
        for plm_missign_bom_id in self:
            plm_missign_bom_id.copy_right_left()
            plm_missign_bom_id.delete_bom_line()


class plm_compare_bom(osv.osv.osv_memory):
    _name = "plm.compare.bom"
    _description = "BoM Comparison"

    name = fields.Char(_('Part Number'), size=64)
    bom_id1 = fields.Many2one('mrp.bom',
                              string=_('BoM 1'),
                              required=True,
                              ondelete='cascade')
    type_id1 = fields.Selection(related="bom_id1.type",
                                string=_('BoM Type'))
    part_id1 = fields.Many2one('product.template',
                               related='bom_id1.product_tmpl_id',
                               string='Part',
                               ondelete='cascade')
    revision1 = fields.Integer(related="part_id1.engineering_revision",
                               string=_("Revision"),
                               store=False)
    description1 = fields.Char(related="part_id1.name",
                               string=_("Description"),
                               store=False)
    bom_id2 = fields.Many2one('mrp.bom',
                              _('BoM 2'),
                              required=True,
                              ondelete='cascade')
    type_id2 = fields.Selection(related="bom_id2.type",
                                string=_('BoM Type'))
    part_id2 = fields.Many2one('product.template',
                               related='bom_id2.product_tmpl_id',
                               string='Part',
                               ondelete='cascade')
    revision2 = fields.Integer(related="part_id2.engineering_revision",
                               string=_("Revision"),
                               store=False)
    description2 = fields.Char(related="part_id2.name",
                               string=_("Description"),
                               store=False)
    anotinb = fields.One2many('plm.adding.bom',
                              'bom_id',
                              _('BoM Adding'))
    bnotina = fields.One2many('plm.missing.bom',
                              'bom_id',
                              _('BoM Missing'))
    compute_type = fields.Selection([('only_product', _('Compare Only Product Existence')),
                                     ('num_qty', _('Compare By Item Number and Quantity')),
                                     ('summarized', _('Compare Product Quantity'))],
                                    default='only_product',
                                    string=_('Compare type'))

    bom_line_id_to_delete = fields.Many2many('mrp.bom.line', string=_('BoM Line to Delete'))

    @api.multi
    def _to_update(self):
        for plm_compare_bom_id in self:
            rule = len(plm_compare_bom_id.bom_line_id_to_delete) or len(plm_compare_bom_id.anotinb.filtered(lambda x: x.reason == 'new')) or len(plm_compare_bom_id.bnotina.filtered(lambda x: x.reason == 'new'))
            plm_compare_bom_id.to_update = True if rule else False

    to_update = fields.Boolean(compute='_to_update')

    @api.multi
    def _are_equal(self):
        for plm_compare_bom_id in self:
            plm_compare_bom_id.bom_are_equal = len(plm_compare_bom_id.anotinb) == 0 and len(plm_compare_bom_id.bnotina) == 0
    bom_are_equal = fields.Boolean(compute='_are_equal')

    @api.multi
    def name_get(self):
        result = []
        for r in self:
            name = "%s .. %s.." % (r.part_id1.name[:8], r.part_id2.name[:8])
            result.append((r.id, name))
        return result

    @api.multi
    def update_bom(self):
        mrp_bom_line = self.env['mrp.bom.line']
        for plm_compare_bom_id in self:
            for plm_missing_id in plm_compare_bom_id.anotinb.filtered(lambda x: x.reason == 'new'):
                mrp_bom_line.create({
                    'bom_id': self.bom_id1.id,
                    'product_qty': plm_missing_id.itemqty,
                    'product_id': plm_missing_id.part_id.id,
                    'type': self.bom_id1.type,
                    'itemnum': len(self.bom_id1.bom_line_ids) + 1})
                plm_missing_id.reason = 'added'
            for plm_adding_id in plm_compare_bom_id.bnotina.filtered(lambda x: x.reason == 'new'):
                mrp_bom_line.create({
                    'bom_id': self.bom_id2.id,
                    'product_qty': plm_adding_id.itemqty,
                    'product_id': plm_adding_id.part_id.id,
                    'type': self.bom_id2.type,
                    'itemnum': len(self.bom_id2.bom_line_ids) + 1})
                plm_adding_id.reason = 'added'
            for mrp_bom_line_id in plm_compare_bom_id.bom_line_id_to_delete:
                mrp_bom_line_id.unlink()

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
        res['compute_type'] = 'only_product'
        return res

    @api.model
    def computeBomLines(self, bomBrws, keyType=None):
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
                          'revision': bomLineBrws.product_id.engineering_revision,
                          }
            if keyType == 'num_qty':
                key = '%s_%s_%s' % (bomLineBrws.product_id.id, bomLineBrws.itemnum, bomLineQty)
            else:
                key = productId
            if key not in bomDict:
                bomDict[key] = [createVals]
            else:
                if keyType == 'summarize':
                    bomDict[key][0]['itemqty'] = bomDict[key][0]['itemqty'] + bomLineQty
                else:
                    bomDict[key].append(createVals)
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
                        toCreateVals['reason'] = 'added'
                        listToAppend.append(funcToCall(toCreateVals))
        leftItems = []
        rightItems = []
        checkAndAdd(bom1Dict, bom2Dict, leftItems, self.getLeftBomObj)
        checkAndAdd(bom2Dict, bom1Dict, rightItems, self.getRightBomObj)
        return leftItems, rightItems

    def computeSummarized(self, bom1Dict, bom2Dict):

        def checkAndAdd(leftDict, rightDict, listToAppend):
            for product_id, toCreateValsList in leftDict.items():
                for toCreateVals in toCreateValsList:  # Always 1 because summarized
                    if product_id not in rightDict:
                        toCreateVals['reason'] = 'added'
                        listToAppend.append(self.getLeftBomObj(toCreateVals))
                    else:
                        qtyLeftDict = toCreateVals['itemqty']
                        qtyRightDict = rightDict[product_id][0]['itemqty']
                        resQty = qtyLeftDict - qtyRightDict
                        toCreateVals['reason'] = 'changed_qty'
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
            toCreateValsList[0]['reason'] = 'added'
            rightItems.append(self.getRightBomObj(toCreateValsList[0]))
        return leftItems, rightItems

    def computeByNumQty(self, bom1Dict, bom2Dict):
        leftItems = []
        rightItems = []
        key1 = set(bom1Dict.keys())
        key2 = set(bom2Dict.keys())
        right = key1 - key2
        left = key2 - key1
        for key in right:
            for toCreateVals in bom1Dict[key]:
                toCreateVals['reason'] = 'changed'
                rightItems.append(self.getLeftBomObj(toCreateVals))
        for key in left:
            for toCreateVals in bom2Dict[key]:
                toCreateVals['reason'] = 'changed'
                leftItems.append(self.getRightBomObj(toCreateVals))
        return rightItems, leftItems

    @api.multi
    def action_compare_Bom(self):
        """
            Compare two BOMs
        """
        logging.info('Start comparing')
        bom1Dict = self.computeBomLines(self.bom_id1, self.compute_type)
        bom2Dict = self.computeBomLines(self.bom_id2, self.compute_type)
        logging.info('Lines computed. Compute type %r' % (self.compute_type))
        if self.compute_type == 'only_product':
            bom1NewItems, bom2NewItems = self.computeOnlyProduct(bom1Dict, bom2Dict)
        elif self.compute_type == 'summarized':
            bom1NewItems, bom2NewItems = self.computeSummarized(bom1Dict, bom2Dict)
        elif self.compute_type == 'num_qty':
            bom1NewItems, bom2NewItems = self.computeByNumQty(bom1Dict, bom2Dict)
        else:
            logging.warning('Compute type not found!')
        logging.info('Starting returning self %r' % (self))
        self.write({'anotinb': [(6, False, bom1NewItems)],
                    'bnotina': [(6, False, bom2NewItems)]})
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
