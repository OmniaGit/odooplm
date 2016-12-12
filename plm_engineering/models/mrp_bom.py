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
Created on 31 Aug 2016

@author: Daniel Smerghetto
'''

from openerp import models
from openerp import fields
from openerp import api
from openerp import _
import logging
import sys


class MrpBomExtension(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def _get_reference_eng_type(self):
        moduleBrwsList = self.env['ir.module.module'].search([('name', '=', 'plm_spare')])
        for modbrws in moduleBrwsList:
            if modbrws.state == 'installed':
                return [('normal', _('Normal BoM')),
                        ('phantom', _('Sets / Phantom')),
                        ('ebom', _('Engineering BoM')),
                        ('spbom', _('Spare BoM'))]
        return [('normal', _('Normal BoM')),
                ('phantom', _('Sets / Phantom')),
                ('ebom', _('Engineering BoM'))]

    type = fields.Selection('_get_reference_eng_type',
                            _('BoM Type'),
                            required=True,
                            default='normal',
                            help=_("Phantom BOM: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product."
                                   "Ship this product as a set of components (kit)."))
    ebom_source_id = fields.Integer('Source Ebom ID')

    @api.model
    def _getinbom(self, pid, sid=False):
        bomLType = self.env['mrp.bom.line']
        bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'ebom')])
        if not bomLineBrwsList:
            bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
            if not bomLineBrwsList:
                bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('source_id', '=', False), ('type', '=', 'ebom')])
            if not bomLineBrwsList:
                bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')])
                if not bomLineBrwsList:
                    bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('type', '=', 'ebom')])
                if not bomLineBrwsList:
                    bomLineBrwsList = bomLType.search([('product_id', '=', pid), ('type', '=', 'normal')])
        return bomLineBrwsList

    @api.model
    def _getbom(self, pid, sid=False):
        if sid is None:
            sid = False
        bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'ebom')])
        if not bomBrwsList:
            bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
            if not bomBrwsList:
                bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('source_id', '=', False), ('type', '=', 'ebom')])
                if not bomBrwsList:
                    bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')])
                    if not bomBrwsList:
                        bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('type', '=', 'ebom')])
                        if not bomBrwsList:
                            bomBrwsList = self.search([('product_tmpl_id', '=', pid), ('type', '=', 'normal')])
        return bomBrwsList

    @api.model
    def SaveStructure(self, relations, level=0, currlevel=0):
        """
            Save EBom relations
        """
        t_bom_line = self.env['mrp.bom.line']
        t_product_product = self.env['product.product']

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
            if not self.search([('product_id', '=', parentID),
                                ('source_id', '=', sourceID)]):
                bomID = saveParent(parentName, parentID, sourceID, kindBom='ebom')
                for parentName, parentID, childName, childID, sourceID, relArgs in subRelations:
                    if parentName == childName:
                        logging.error('toCompute : Father (%s) refers to himself' % (str(parentName)))
                        raise Exception(_('saveChild.toCompute : Father "%s" refers to himself' % (str(parentName))))

                    saveChild(childName, childID, sourceID, bomID, kindBom='ebom', args=relArgs)
                    toCompute(childName, nexRelation)
                self.RebaseProductWeight(bomID, self.browse(bomID).rebaseBomWeight())
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
                objPart = t_product_product.with_context({}).browse(partID)
                res['product_tmpl_id'] = objPart.product_tmpl_id.id
                res['product_id'] = partID
                res['source_id'] = sourceID
                if args is not None:
                    for arg in args:
                        res[str(arg)] = args[str(arg)]
                if ('product_qty' in res):
                    res['product_qty'] = repairQty(res['product_qty'])
                return self.create(res).id
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
                return t_bom_line.create(res)
            except Exception, ex:
                logging.error(ex)
                logging.error("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(args)))
                raise AttributeError(_("saveChild :  unable to create a relation for part (%s) with source (%d) : %s." % (name, sourceID, str(sys.exc_info()))))

        if len(relations) < 1:  # no relation to save
            return False
        parentName, _parentID, _childName, _childID, _sourceID, _relArgs = relations[0]
        toCleanRelations(relations)
        toCompute(parentName, relations)
        return False

MrpBomExtension()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
