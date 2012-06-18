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

class plm_component(osv.osv):
    _inherit = 'product.product'

##  Specialized Actions callable interactively
    def action_create_spareBom(self, cr, uid, ids, context=None):
        """
            Create a new Spare Bom if doesn't exist (action callable from views)
        """
        if not 'active_id' in context:
            return False
        return self.action_create_spareBom_WF(cr, uid, context['active_ids'])

    def action_check_spareBom(self, cr, uid, ids, context=None):
        """
            Check if a Spare Bom exists (action callable from views)
        """
        global RETDMESSAGE
        if not 'active_id' in context:
            return False
        if self.action_check_spareBom_WF(cr, uid, context['active_ids'], context):
            logMessage=_('Following Parts are without Spare BOM :')+'\n'+RETDMESSAGE
            raise osv.except_osv(_('Check on Spare Bom'), logMessage)
        return False

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
            objBom=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision),('type','=','spbom')])
        else:
            objBom=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','spbom')])
        defaults={}
        if not objBom:
            idBom=False
            if checkObj.std_description.bom_tmpl:
                idBom=bomType.copy(cr, uid, checkObj.std_description.bom_tmpl.id, defaults, context)
            if idBom:
                bomType.write(cr,uid,[idBom],{'name':checkObj.name,'product_id':checkObj.id,'type':'spbom',},context=None)
                oidBom=bomType.browse(cr,uid,idBom,context=context)
                for bom_line in oidBom.bom_lines:
#                    bom_line.product_id
                    bomType.write(cr,uid,[bom_line.id],{'type':'spbom','source_id':False,'name':bom_line.name.replace(' Copy',''),},context=None)

        if checkObj.engineering_revision:
            idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision)],('type','=','ebom'))
        else:
            idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','ebom')])
        if not idBoms:
            if checkObj.engineering_revision:
                idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision)],('type','=','normal'))
            else:
                idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','normal')])
        for idBom in idBoms:
            for bom_line in bomType.browse(cr,uid,idBom,context=context).bom_lines:
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
                objBom=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision),('type','=','spbom')])
            else:
                objBom=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','spbom')])
            if not objBom:
                RETDMESSAGE=RETDMESSAGE+"%s/%d \n" %(checkObj.name,checkObj.engineering_revision)

        if checkObj.engineering_revision:
            idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision)],('type','=','ebom'))
        else:
            idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','ebom')])
        if not idBoms:
            if checkObj.engineering_revision:
                idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision)],('type','=','normal'))
            else:
                idBoms=bomType.search(cr, uid, [('name','=',checkObj.name),('type','=','normal')])
            
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

