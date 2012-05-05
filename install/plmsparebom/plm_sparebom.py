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
RETDMESSAGE=''

class plm_component(osv.osv):
    _inherit = 'product.product'

##  Specialized Actions callable interactively
    def action_create_spareBom(self, cr, uid, ids, context=None):
        """
            Create a new Spare Bom (if it doesn't already exist)
        """
        if not 'active_id' in context:
            return False
        checkObj=self.browse(cr, uid, context['active_id'])
        if '-Spare' in checkObj.name:
            return False
        bomType=self.pool.get('mrp.bom')
        if checkObj.engineering_revision:
            objBom=bomType.search(cr, uid, [('name','=',checkObj.name+'-Spare'),('engineering_revision','=',checkObj.engineering_revision)])
        else:
            objBom=bomType.search(cr, uid, [('name','=',checkObj.name+'-Spare')])
        defaults={}
        if not objBom:
            idBom=False
            if checkObj.std_description.bom_tmpl:
                idBom=bomType.copy(cr, uid, checkObj.std_description.bom_tmpl.id, defaults, context)
            if idBom:
                bomType.write(cr,uid,[idBom],{'name':checkObj.name+"-Spare",'product_id':checkObj.id,},context=None)
                oidBom=bomType.browse(cr,uid,idBom,context=context)
                for bom_line in oidBom.bom_lines:
#                    bom_line.product_id
                    bomType.write(cr,uid,[bom_line.id],{'source_id':False,'name':bom_line.name.replace(' Copy',''),},context=None)
        return False

    def action_check_spareBom(self, cr, uid, ids, context=None):
        """
            Check if a Spare Bom exists (action callable from views)
        """
        if not 'active_id' in context:
            return False
        if self.action_check_spareBom_WF(cr, uid, [context['active_id']], context):
            logMessage=_('Following Parts are without Spare BOM :')+'\n'+RETDMESSAGE
            raise osv.except_osv(_('Check on Spare Bom'), logMessage)
        return False

#  Work Flow Actions
    def action_check_spareBom_WF(self, cr, uid, ids, context=None):
        """
            Check if a Spare Bom exists (action callable from code)
        """
        RETDMESSAGE=''
        for id in ids:
            self._check_spareBom(cr, uid, id, context)
        if len(RETDMESSAGE)>0:
            return True
        return False

#   Internal methods
    def _check_spareBom(self, cr, uid, oid, context=None):
        """
            Check if a Spare Bom exists (recursive on all EBom children)
        """
        bomType=self.pool.get('mrp.bom')
        checkObj=self.browse(cr, uid, oid, context)
        if checkObj.std_description.bom_tmpl:
            if checkObj.engineering_revision:
                objBom=bomType.search(cr, uid, [('name','=',checkObj.name+'-Spare'),('engineering_revision','=',checkObj.engineering_revision)])
            else:
                objBom=bomType.search(cr, uid, [('name','=',checkObj.name+'-Spare')])
            if not objBom:
                RETDMESSAGE=RETDMESSAGE+checkObj.name+'/'+checkObj.engineering_revision+'\n'

        if checkObj.engineering_revision:
            objEBom=bomType.search(cr, uid, [('name','=',checkObj.name),('engineering_revision','=',checkObj.engineering_revision)])
        else:
            objEBom=bomType.search(cr, uid, [('name','=',checkObj.name)])
        if objEBom:
            for bom_line in objEBom.bom_lines:
                self._check_spareBom(cr, uid, bom_line.product_id, context)
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

