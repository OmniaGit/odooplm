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
from openerp.tools  import DEFAULT_SERVER_DATE_FORMAT
from openerp        import models, fields, api, SUPERUSER_ID, _, osv
import logging
_logger = logging.getLogger(__name__)

def _moduleName():
    path = os.path.dirname(__file__)
    return os.path.basename(os.path.dirname(path))
openerpModule=_moduleName()

class plm_document(models.Model):
    _name               = 'plm.document'
    _inherit            = ['mail.thread','plm.document']
    
    linkedcomponents    = fields.Many2many('product.product', 'plm_component_document_rel','document_id','component_id', _('Linked Parts'))
    
    _defaults           = {
                             'state': lambda *a: 'draft',
                             'res_id': lambda *a: False,
                             }
plm_document()


class plm_component(models.Model):
    _name       = 'product.product'
    _inherit    = 'product.product'

    @api.multi
    def _father_part_compute(self, name='', arg={}):
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
        bom_line_objType = self.env['mrp.bom.line']
        prod_objs = self.browse(self.ids)
        for prod_obj in prod_objs:
            prod_ids = []
            bom_line_objs = bom_line_objType.search([('product_id', '=', prod_obj.id)])
            for bom_line_obj in bom_line_objs:
                for objPrd in self.search([('product_tmpl_id', '=', bom_line_obj.bom_id.product_tmpl_id.id)]):
                    prod_ids.append(objPrd.id)
            prod_obj.father_part_ids = prod_ids

    linkeddocuments = fields.Many2many('plm.document', 'plm_component_document_rel', 'component_id', 'document_id', _('Linked Docs'))
    tmp_material = fields.Many2one('plm.material', _('Raw Material'), required=False, change_default=True, help=_("Select raw material for current product"))
    tmp_surface = fields.Many2one('plm.finishing', _('Surface Finishing'), required=False, change_default=True, help=_("Select surface finishing for current product"))
    father_part_ids = fields.Many2many('product.product', compute=_father_part_compute, string=_("BoM Hierarchy"), store=False)

    def on_change_tmpmater(self, cr, uid, ids, tmp_material=False):
        values = {'engineering_material': ''}
        if tmp_material:
            thisMaterial = self.pool.get('plm.material')
            thisObject = thisMaterial.browse(cr, uid, tmp_material)
            if thisObject.name:
                values['engineering_material'] = unicode(thisObject.name)
        return {'value': values}

    def on_change_tmptreatment(self, cr, uid, ids, tmp_treatment=False):
        values = {'engineering_treatment': ''}
        if tmp_treatment:
            thisTreatment = self.pool.get('plm.treatment')
            thisObject = thisTreatment.browse(cr, uid, tmp_treatment)
            if thisObject.name:
                values['engineering_treatment'] = unicode(thisObject.name)
        return {'value': values}

    def on_change_tmpsurface(self, cr, uid, ids, tmp_surface=False):
        values = {'engineering_surface': ''}
        if tmp_surface:
            thisSurface = self.pool.get('plm.finishing')
            thisObject = thisSurface.browse(cr, uid, tmp_surface)
            if thisObject.name:
                values['engineering_surface'] = unicode(thisObject.name)
        return {'value': values}
plm_component()


class plm_relation(models.Model):
    _name       = 'mrp.bom'
    _inherit    = 'mrp.bom'

#######################################################################################################################################33

#   Overridden methods for this entity

    def _bom_find(self, cr, uid, product_tmpl_id=None, product_id=None, properties=None, context=None):
        """ Finds BoM for particular product and product uom.
        @param product_tmpl_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        bom_id = super(plm_relation, self)._bom_find(cr,
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

#######################################################################################################################################33
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
        bom_type=''
        bom_line_objType = self.env['mrp.bom.line']
        for bom_obj in self:
            result = []
            bom_type=bom_obj.type
            if bom_type=='':
                bom_children = bom_line_objType.search([('product_id','=',bom_obj.product_id.id)])
            else:
                bom_children = bom_line_objType.search([('product_id','=',bom_obj.product_id.id),('type','=',bom_type)])
            for bom_child in bom_children:
                if bom_child.bom_id.id:
                    if not(bom_child.bom_id.id in result):
                        result.extend([bom_child.bom_id.id])
            bom_obj.father_complete_ids = self.env['mrp.bom'].browse(list(set(result)))

    state                   = fields.Selection  (related="product_tmpl_id.state",                string=_("Status"),     help=_("The status of the product in its LifeCycle."),  store=False)
    engineering_revision    = fields.Integer    (related="product_tmpl_id.engineering_revision", string=_("Revision"),   help=_("The revision of the product."),                 store=False)
    description             = fields.Text       (related="product_tmpl_id.description",          string=_("Description"),                                                        store=False)
    father_complete_ids     = fields.Many2many  ('mrp.bom', compute=_father_compute,        string=_("BoM Hierarchy"),                                                     store=False)

plm_relation()

class plm_relation_line(models.Model):
    _name       = 'mrp.bom.line'
    _inherit    = 'mrp.bom.line'
    _order      = "itemnum"

    @api.one
    def _get_child_bom_lines(self):
        """
            If the BOM line refers to a BOM, return the ids of the child BOM lines
        """
        bom_obj = self.env['mrp.bom']
        for bom_line in self:
            for bom_id in self.search([('product_id', '=', bom_line.product_id.id),
                                      ('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                                      ('type', '=', bom_line.type)]):
                child_bom = bom_obj.browse(bom_id)
                for childBomLine in child_bom.bom_line_ids:
                    childBomLine._get_child_bom_lines()
                self.child_line_ids = [x.id for x in child_bom.bom_line_ids]
                return
            else:
                self.child_line_ids = False

    state                   =   fields.Selection    (related="product_id.state",                string=_("Status"),     help=_("The status of the product in its LifeCycle."),  store=False)
    engineering_revision    =   fields.Integer      (related="product_id.engineering_revision", string=_("Revision"),   help=_("The revision of the product."),                 store=False)
    description             =   fields.Text         (related="product_id.description",          string=_("Description"),                                                        store=False)
    weight_net              =   fields.Float        (related="product_id.weight",               string=_("Weight Net"),                                                         store=False)

plm_relation_line()

class plm_document_relation(models.Model):
    _name           =   'plm.document.relation'
    _inherit        =   'plm.document.relation'
    
    parent_preview  =   fields.Binary   (related="parent_id.preview",       string=_("Preview"),    store=False)
    parent_state    =   fields.Selection(related="parent_id.state",         string=_("Status"),     store=False)
    parent_revision =   fields.Integer  (related="parent_id.revisionid",    string=_("Revision"),   store=False)
    child_preview   =   fields.Binary   (related="child_id.preview",        string=_("Preview"),    store=False)
    child_state     =   fields.Selection(related="child_id.state",          string=_("Status"),     store=False)
    child_revision  =   fields.Integer  (related="child_id.revisionid",     string=_("Revision"),   store=False)

plm_document_relation()

