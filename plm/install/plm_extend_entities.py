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
        prod_ids=[]
        bom_line_objType = self.env['mrp.bom.line']
        prod_objs = self.browse(self.ids)
        for prod_obj in prod_objs:
            bom_line_objs = bom_line_objType.search([('product_id','=',prod_obj.id)])
            for bom_line_obj in bom_line_objs:                
                prod_ids.extend([bom_line_obj.bom_id.product_id.id])
        self.father_part_ids = self.env['product.product'].browse(list(set(prod_ids)))

    linkeddocuments = fields.Many2many  ('plm.document', 'plm_component_document_rel','component_id','document_id', _('Linked Docs'))  
    tmp_material    = fields.Many2one   ('plm.material',_('Raw Material'), required=False, change_default=True, help=_("Select raw material for current product"))
    #tmp_treatment   = fields.Many2one('plm.treatment',_('Thermal Treatment'), required=False, change_default=True, help=_("Select thermal treatment for current product"))
    tmp_surface     = fields.Many2one   ('plm.finishing',_('Surface Finishing'), required=False, change_default=True, help=_("Select surface finishing for current product"))
    father_part_ids = fields.Many2many  ('product.product', compute = _father_part_compute, string=_("BoM Hierarchy"), store =False)

    def on_change_tmpmater(self, cr, uid, ids, tmp_material=False):
        values={'engineering_material':''}
        if tmp_material:
            thisMaterial=self.pool.get('plm.material')
            thisObject=thisMaterial.browse(cr, uid, tmp_material)
            if thisObject.name:
                values['engineering_material']=thisObject.name
        return {'value': {'engineering_material':str(values['engineering_material'])}}

    def on_change_tmptreatment(self, cr, uid, ids, tmp_treatment=False):
        values={'engineering_treatment':''}
        if tmp_treatment:
            thisTreatment=self.pool.get('plm.treatment')
            thisObject=thisTreatment.browse(cr, uid, tmp_treatment)
            if thisObject.name:
                values['engineering_treatment']=thisObject.name
        return {'value': {'engineering_treatment':str(values['engineering_treatment'])}}

    def on_change_tmpsurface(self, cr, uid, ids, tmp_surface=False):
        values={'engineering_surface':''}
        if tmp_surface:
            thisSurface=self.pool.get('plm.finishing')
            thisObject=thisSurface.browse(cr, uid, tmp_surface)
            if thisObject.name:
                values['engineering_surface']=thisObject.name
        return {'value': {'engineering_surface':str(values['engineering_surface'])}}
plm_component()


class plm_relation(models.Model):
    _name       = 'mrp.bom'
    _inherit    = 'mrp.bom'

#######################################################################################################################################33

#   Overridden methods for this entity

    def _bom_find(self, cr, uid, product_tmpl_id=None, product_id=None, properties=None, bomType='normal',context=None):
        """ Finds BoM for particular product and product uom.
        @param product_tmpl_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        if properties is None:
            properties = []
        if product_id:
            domain = ['&',('type', '=', bomType)]
            if not product_tmpl_id:
                product_tmpl_id = self.pool['product.product'].browse(cr, uid, product_id, context=context).product_tmpl_id.id
            domain = domain + [
                '|',
                    ('product_id', '=', product_id),
                    '&',
                        ('product_id', '=', False),
                        ('product_tmpl_id', '=', product_tmpl_id)
            ]
        elif product_tmpl_id:
            domain = domain + [('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]
        else:
            # neither product nor template, makes no sense to search
            return False
        domain = domain + [ '|', ('date_start', '=', False), ('date_start', '<=', time.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                            '|', ('date_stop', '=', False), ('date_stop', '>=', time.strftime(DEFAULT_SERVER_DATE_FORMAT))]
        # order to prioritize bom with product_id over the one without
        ids = self.search(cr, uid, domain, order='product_id', context=context)
        # Search a BoM which has all properties specified, or if you can not find one, you could
        # pass a BoM without any properties
        bom_empty_prop = False
        for bom in self.pool.get('mrp.bom').browse(cr, uid, ids, context=context):
            if not set(map(int, bom.property_ids or [])) - set(properties or []):
                if properties and not bom.property_ids:
                    bom_empty_prop = bom.id
                else:
                    return bom.id
        return bom_empty_prop
    
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
 
    state                   = fields.Selection  (related="product_id.state",            string=_("Status"),     help=_("The status of the product in its LifeCycle."),  store=False)
    engineering_revision    = fields.Char       (related="product_id.engineering_code", string=_("Revision"),   help=_("The revision of the product."),                 store=False)
    description             = fields.Text       (related="product_id.description",      string=_("Description"),                                                        store=False)
    father_complete_ids     = fields.Many2many  ('mrp.bom', compute=_father_compute,    string=_("BoM Hierarchy"),                  store=False)

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
        bom_obj = self.pool['mrp.bom']
        res = {}
        for bom_line in self.browse(self.ids):
            bom_id = bom_obj._bom_find(
                                        self.env.cr,
                                        self.env.uid,
                                        product_tmpl_id=bom_line.product_id.product_tmpl_id.id,
                                        product_id=bom_line.product_id.id, 
                                        bomType=bom_line.type)
            if bom_id:
                child_bom = bom_obj.browse(self.env.cr, self.env.uid, bom_id)
                for childBomLine in child_bom.bom_line_ids:
                    res[childBomLine.id]=childBomLine._get_child_bom_lines()
                res[bom_line.id] = [x.id for x in child_bom.bom_line_ids] #child_bom.bom_line_ids[0]._get_child_bom_lines()
            else:
                res[bom_line.id] = False
        return res

    state                   =   fields.Selection    (related="product_id.state",                string=_("Status"),     help=_("The status of the product in its LifeCycle."),  store=False)
    engineering_revision    =   fields.Integer      (related="product_id.engineering_revision", string=_("Revision"),   help=_("The revision of the product."),                 store=False)
    description             =   fields.Text         (related="product_id.description",          string=_("Description"),                                                        store=False)
    weight_net              =   fields.Float        (related="product_id.weight",               string=_("Weight Net"),                                                         store=False)
    child_line_ids          =   fields.One2many     ("mrp.bom.line",compute=_get_child_bom_lines,string=_("BOM lines of the referred bom"))


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

