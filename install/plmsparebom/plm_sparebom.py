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

class plm_component(osv.osv):
    _inherit = 'product.product'

##  Specialized Actions
    def action_create_spareBom(self, cr, uid, ids, context=None):
        """
            Create a new Spare Bom (if it doesn't already exist)
        """
        bomType=self.pool.get('mrp.bom')
        checkObj=self.browse(cr, uid, context['active_id'])
        if '-Spare' in checkObj.name:
            return False
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

