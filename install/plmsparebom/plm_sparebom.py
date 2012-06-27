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
from tools.translate import _

RETDMESSAGE=''

class plm_temporary(osv.osv_memory):
    _inherit = "plm.temporary"
##  Specialized Actions callable interactively
    def action_create_spareBom(self, cr, uid, ids, context=None):
        """
            Create a new Spare Bom if doesn't exist (action callable from views)
        """
        if not 'active_id' in context:
            return False
        self.pool.get('product.product').action_create_spareBom_WF(cr, uid, context['active_ids'])

        return {
              'name': _('Bill of Materials'),
              'view_type': 'form',
              "view_mode": 'tree,form',
              'res_model': 'mrp.bom',
              'type': 'ir.actions.act_window',
              'domain': "[('product_id','in', ["+','.join(map(str,context['active_ids']))+"])]",
         }
    
    def action_check_spareBom(self, cr, uid, ids, context=None):
        """
            Check if a Spare Bom exists (action callable from views)
        """
        global RETDMESSAGE
        if not 'active_id' in context:
            return False
        if self.pool.get('product.product').action_check_spareBom_WF(cr, uid, context['active_ids'], context):
            logMessage=_('Following Parts are without Spare BOM :')+'\n'+RETDMESSAGE
            raise osv.except_osv(_('Check on Spare Bom'), logMessage)

        return {
              'name': _('Engineering Parts'),
              'view_type': 'form',
              "view_mode": 'tree,form',
              'res_model': 'product.product',
              'type': 'ir.actions.act_window',
              'domain': "[('id','in', ["+','.join(map(str,context['active_ids']))+"])]",
         }
    
plm_temporary()

class plm_component(osv.osv):
    _inherit = 'product.product'

#  Work Flow Actions
    def action_create_spareBom_WF(self, cr, uid, ids, context=None):
        """
            Create a new Spare Bom if doesn't exist (action callable from code)
        """
        for idd in ids:
            self._create_spareBom(cr, uid, idd, context)
        return False

    def action_check_spareBom_WF(self, cr, uid, ids, context=None):
        """
            Check if a Spare Bom exists (action callable from code)
        """
        global RETDMESSAGE
        RETDMESSAGE=''
        for idd in ids:
            self._check_spareBom(cr, uid, idd, context)
        if len(RETDMESSAGE)>0:
            return True
        return False

#   Internal methods
    def _create_spareBom(self, cr, uid, idd, context=None):
        """
            Create a new Spare Bom (recursive on all EBom children)
        """
        checkObj=self.browse(cr, uid, idd, context)
        if not checkObj:
            return False
        if '-Spare' in checkObj.name:
            return False
        bomType=self.pool.get('mrp.bom')
        if checkObj.engineering_revision:
            objBom=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision),('type','=','spbom'),('bom_id','=',False)])
            idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision),('type','=','ebom'),('bom_id','=',False)])
        else:
            objBom=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','spbom'),('bom_id','=',False)])
            idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','ebom'),('bom_id','=',False)])
        defaults={}
        if not objBom:
            for idBom in idBoms:
                if checkObj.std_description.bom_tmpl:
                    newidBom=bomType.copy(cr, uid, checkObj.std_description.bom_tmpl.id, defaults, context)
                else:
                    newidBom=bomType.copy(cr, uid, idBom, defaults, context)
                if newidBom:
                    bomType.write(cr,uid,[newidBom],{'name':checkObj.name,'product_id':checkObj.id,'type':'spbom',},context=None)
                    oidBom=bomType.browse(cr,uid,newidBom,context=context)
                    for bom_line in oidBom.bom_lines:
                        bomType.write(cr,uid,[bom_line.id],{'type':'spbom','source_id':False,'name':bom_line.name.replace(' Copy',''),},context=None)
                        self._create_spareBom(cr, uid, bom_line.product_id.id, context)
        return False

    def _check_spareBom(self, cr, uid, idd, context=None):
        """
            Check if a Spare Bom exists (recursive on all EBom children)
        """
        global RETDMESSAGE
        bomType=self.pool.get('mrp.bom')
        checkObj=self.browse(cr, uid, idd, context)
        if not checkObj:
            return False
        if checkObj.std_description.bom_tmpl:
            if checkObj.engineering_revision:
                objBom=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision),('type','=','spbom'),('bom_id','=',False)])
            else:
                objBom=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','spbom'),('bom_id','=',False)])
            if not objBom:
                RETDMESSAGE=RETDMESSAGE+"%s/%d \n" %(checkObj.name,checkObj.engineering_revision)

        if checkObj.engineering_revision:
            idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision),('type','=','ebom'),('bom_id','=',False)])
        else:
            idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','ebom')])
        if not idBoms:
            if checkObj.engineering_revision:
                idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision),('type','=','normal'),('bom_id','=',False)])
            else:
                idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','normal'),('bom_id','=',False)])
            
        for idBom in idBoms:
            for bom_line in bomType.browse(cr,uid,idBom,context=context).bom_lines:
                self._check_spareBom(cr, uid, bom_line.product_id.id, context)
        return False

plm_component()


class plm_description(osv.osv):
    _inherit = "plm.description"
    _columns = {
                'bom_tmpl': fields.many2one('mrp.bom','Template BOM', required=False, change_default=True, help="Select a template BOM to drive Spare BOM."),
    }
    _defaults = {
                 'bom_tmpl': lambda *a: False,
    }
#       Introduced relationship with mrp.bom to implement Spare Part Bom functionality
    
plm_description()

