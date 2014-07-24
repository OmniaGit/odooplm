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

from types import *

from openerp.osv import osv, fields
from openerp.tools.translate import _

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
    
plm_temporary()

class plm_component(osv.osv):
    _inherit = 'product.product'

#  Work Flow Actions
    def action_create_spareBom_WF(self, cr, uid, ids, context=None):
        """
            Create a new Spare Bom if doesn't exist (action callable from code)
        """
        for idd in ids:
            self.processedIds=[]
            self._create_spareBom(cr, uid, idd, context)
        return False

#   Internal methods
    def _create_spareBom(self, cr, uid, idd, context=None):
        """
            Create a new Spare Bom (recursive on all EBom children)
        """
        newidBom=False
        sourceBomType='ebom'
        if idd in self.processedIds:
            return False
        self.processedIds.append(idd)
        checkObj=self.browse(cr, uid, idd, context)
        if not checkObj:
            return False
        if '-Spare' in checkObj.name:
            return False
        if (type(context) is DictType) and ('sourceBomType' in context):
            sourceBomType=context['sourceBomType']
        bomType=self.pool.get('mrp.bom')
        bomLType=self.pool.get('mrp.bom.line')
        objBoms=bomType.search(cr, uid, [('product_id','=',idd),('type','=','spbom')])
        idBoms=bomType.search(cr, uid, [('product_id','=',idd),('type','=','normal')])
        if not idBoms:
            idBoms=bomType.search(cr, uid, [('product_id','=',idd),('type','=',sourceBomType)])

        defaults={}
        if not objBoms:
            if checkObj.std_description.bom_tmpl:
                newidBom=bomType.copy(cr, uid, checkObj.std_description.bom_tmpl.id, defaults, context)
            if (not newidBom) and idBoms:
                    newidBom=bomType.copy(cr, uid, idBoms[0], defaults, context)
            if newidBom:
                bomType.write(cr,uid,[newidBom],{'name':checkObj.name,'product_id':checkObj.id,'type':'spbom',},context=None)
                oidBom=bomType.browse(cr,uid,newidBom,context=None)
                
                ok_rows=self._summarizeBom(cr, uid, oidBom.bom_line_ids)
                for bom_line in list(set(oidBom.bom_line_ids) ^ set(ok_rows)):
                    bomLType.unlink(cr,uid,[bom_line.id],context=None)
                for bom_line in ok_rows:
                    bomLType.write(cr,uid,[bom_line.id],{'type':'spbom','source_id':False,'name':bom_line.product_id.name,'product_qty':bom_line.product_qty,},context=None)
                    self._create_spareBom(cr, uid, bom_line.product_id.id, context)
        else:
            for bom_line in bomType.browse(cr,uid,objBoms[0],context=context).bom_lines:
                self._create_spareBom(cr, uid, bom_line.product_id.id, context=context)
        return False

plm_component()


class plm_description(osv.osv):
    _inherit = "plm.description"
    _columns = {
                'bom_tmpl': fields.many2one('mrp.bom','Choose a BoM', required=False, change_default=True, help="Select a  BoM as template to drive building Spare BoM."),
    }
    _defaults = {
                 'bom_tmpl': lambda *a: False,
    }
#       Introduced relationship with mrp.bom to implement Spare Part Bom functionality
    
plm_description()

