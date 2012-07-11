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

from osv import osv, fields


class plm_document(osv.osv):
    _inherit = 'ir.attachment'
    _columns = {
                'linkedcomponents':fields.many2many('product.product', 'plm_component_document_rel','document_id','component_id', 'Linked Parts'),
    }    
    _defaults = {
                 'state': lambda *a: 'draft',
                 'res_id': lambda *a: False,
    }    
plm_document()


class plm_component(osv.osv):
    _inherit = 'product.product'
    _columns = {
        	    'linkeddocuments':fields.many2many('ir.attachment', 'plm_component_document_rel','component_id','document_id', 'Linked Docs'),  
                'tmp_material': fields.many2one('plm.material','Raw Material', required=False, change_default=True, help="Select raw material for current product"),
#                'tmp_treatment': fields.many2one('plm.treatment','Thermal Treatment', required=False, change_default=True, help="Select thermal treatment for current product"),
                'tmp_surface': fields.many2one('plm.finishing','Surface Finishing', required=False, change_default=True, help="Select surface finishing for current product")
               }
 
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


class plm_relation(osv.osv):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

    def _child_compute(self, cr, uid, ids, name, arg, context=None):
        """ Gets child bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        result = {}
        if context is None:
            context = {}
        bom_obj = self.pool.get('mrp.bom')
        bom_id = context and context.get('active_id', False) or False
        cr.execute('select id from mrp_bom')
        if all(bom_id != r[0] for r in cr.fetchall()):
            ids.sort()
            bom_id = ids[0]
        bom_parent = bom_obj.browse(cr, uid, bom_id, context=context)
        for bom in self.browse(cr, uid, ids, context=context):
            if (bom_parent) or (bom.id == bom_id):
                result[bom.id] = map(lambda x: x.id, bom.bom_lines)
            else:
                result[bom.id] = []
            if bom.bom_lines:
                continue
            ok = ((name=='child_complete_ids') and (bom.product_id.supply_method=='produce'))
            if (bom.type=='phantom' or ok):
                sids = bom_obj.search(cr, uid, [('bom_id','=',False),('product_id','=',bom.product_id.id),('type','=',bom.type)])
                # Added type to search to avoid to mix different kinds of BoM. 
                if sids:
                    bom2 = bom_obj.browse(cr, uid, sids[0], context=context)
                    result[bom.id] += map(lambda x: x.id, bom2.bom_lines)

        return result

    _columns = {
                'state': fields.related('product_id','state',type="char",relation="product.template",string="Status",store=False),
                'engineering_revision': fields.related('product_id','engineering_revision',type="char",relation="product.template",string="Revision",store=False),
                'description': fields.related('product_id','description',type="char",relation="product.template",string="Description",store=False),
                'weight_net': fields.related('product_id','weight_net',type="float",relation="product.product",string="Weight Net",store=False),
                'uom_id': fields.related('product_id','uom_id',type="integer",relation="product.product",string="Unit of Measure",store=False),
                'child_complete_ids': fields.function(_child_compute, relation='mrp.bom', method=True, string="BoM Hierarchy", type='many2many'),
               }

plm_relation()
