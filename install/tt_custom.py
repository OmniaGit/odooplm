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
from osv import osv, fields
from tools.translate import _
from datetime import datetime


##              Tomorrow Technology customizations

#USED_STATES=[('draft','Draft'),('confirmed','Confirmed'),('released','Released'),('undermodify','UnderModify'),('canceled','Canceled')]
#STATEFORRELEASE=['confirmed']
#STATESRELEASABLE=['confirmed','transmitted','released','undermodify','UnderModify']

class plm_document(osv.osv):
    _inherit = 'ir.attachment'
    _columns = {
                 'comment': fields.char('Revision Note',size=512),
    }    
    _defaults = {
                 'comment': lambda *a: False,
    }    
##              Work Flow Actions

#    def action_transmit(self,cr,uid,ids,context=None):
#        """
#            action to be executed for Transmitted state
#            transmit the object to ERP Metodo
#        """
#        defaults={}
#        defaults['writable']=False
#        defaults['state']='transmitted'
#        pass

plm_document()


class plm_component(osv.osv):
    _inherit = 'product.product'
    _columns = {
                'category': fields.integer('Category'),
                'comp_type': fields.selection([('A','Assembly'),('S','Sub Assembly / Group'),('P','Part')],'Part Type', required=True, translate=True, help="Specify the type of Part"),
                'auto_code1': fields.many2one('plm.number1','Machine Code', required=False, change_default=True, help="Select part to build Part Number"),
                'auto_code2': fields.many2one('plm.number2','Machine Index', required=False, change_default=True, help="Change manually to add new Machine"),
                'auto_code3': fields.many2one('plm.number3','Group Code', required=False, change_default=True, help="Select part to build Part Number"),
                'auto_code4': fields.many2one('plm.number4','Group Index', required=False, change_default=True, help="It will be evaluated automatically to build Part Number"),
                'auto_code5': fields.many2one('plm.number5','Category', required=False, change_default=True, help="Select part to build Part Number"),
                'auto_code6': fields.many2one('plm.number6','Type', required=False, change_default=True, help="Select part to build Part Number"),
                'auto_code7': fields.many2one('plm.number7','Index', required=False, change_default=True, help="It will be evaluated automatically to build Part Number"),
                'auto_code8': fields.many2one('plm.number8','Version', required=False, change_default=True, help="Specify version to build Part Number")
    }
    _defaults = {
                 'comp_type': lambda *a: 'P',
    }

##              Work Flow internal methods
    def _output_data(self,cr,uid,ids,allIDs):
        """
            action to be executed for Transmitted state.
            Transmit the object to ERP Metodo
        """
        defaults=[]
        anag_fields=['name','description']
        rel_fields=['bom_id','product_id','product_qty','itemnum']
        return self._extract_data(cr,uid,ids,allIDs, anag_fields, rel_fields)

##              Work Flow Actions
    def action_transmit(self,cr,uid,ids,context=None):
        """
            action to be executed for Transmitted state.
            Transmit the object to ERP Metodo
        """
        defaults={}
        defaults['engineering_writable']=False
        defaults['state']='transmitted'
        excludeStatuses=['draft','transmitted','released','undermodify','canceled']
        includeStatuses=['confirmed']
        stopFlag,allIDs=self._get_recursive_parts(cr, uid, ids, excludeStatuses, includeStatuses)
        self._action_ondocuments(cr,uid,allIDs,'transmit')
        #TODO : Add sendmail to Purchase to remember to complete work.
        if not self._output_data(cr, uid, ids, allIDs):
            return False
        return self.write(cr, uid, allIDs, defaults, context=context, check=False)

##              Customized Automations

    def on_change_clean_compose(self, cr, uid, id, comp_type=False):
        return {'value': {'auto_code3': False, 'auto_code4':False}}            

    def on_change_code1(self, cr, uid, id, auto_code=False):
        if auto_code:
            thisNumber=self.pool.get('plm.number1')
            thisObject=thisNumber.browse(cr, uid, auto_code)
            nextType=self.pool.get('plm.number2')
            existingIDs=nextType.search(cr, uid, [('auto_code','=',thisObject.auto_code)])
            for id in existingIDs:
                return {'value': {'auto_code2': id, 'category':thisObject.category}}            
        return {}

    def on_change_code3(self, cr, uid, id, auto_code1=False, auto_code2=False, auto_code3=False, comp_type=False):
        if auto_code1 and auto_code2 and auto_code3 and comp_type:
            defaults={}
            thisMachine=self.pool.get('plm.number1').browse(cr, uid, auto_code1)
            thisMachineNum=self.pool.get('plm.number2').browse(cr, uid, auto_code2)
            thisGroup=self.pool.get('plm.number3').browse(cr, uid, auto_code3)
            nextType=self.pool.get('plm.number4')
            seq_name=thisMachine.name+thisMachineNum.name+thisGroup.name
            existingIDs=nextType.search(cr, uid, [('auto_code','=',seq_name),('comp_type','=',comp_type)])
            if not existingIDs:
                if comp_type=='A':
                    defaults['name']="00"
                elif comp_type=='S':
                    defaults['name']="90"
                else:
                    defaults['name']="01"
                defaults['description']='Part Number'+seq_name
                defaults['auto_code']=seq_name
                defaults['comp_type']=comp_type
                id4=nextType.create(cr,uid,defaults)
            else:
                id4 = existingIDs[0]
                if comp_type=='A':                  # It already exist so no new assembly can be coded !!!
                    return {}
                PartNum=nextType.browse(cr, uid, id4)
                Progressive=int(PartNum.name)
                if comp_type=='P':
                    if Progressive<9:
                        defaults['name']="0"+str(Progressive+1)
                    elif Progressive<89:
                        defaults['name']=str(Progressive+1)
                    else:
                        return {}
                elif comp_type=='S':
                    if Progressive<99:
                         defaults['name']=str(Progressive+1)
                    else:
                        return {}
                nextType.write(cr,uid,id4,defaults)

            seq_name=seq_name+str(defaults['name'])
            existingIDs=self.search(cr, uid, [('name','=',seq_name)])
            if not existingIDs:
                defaults['name']=seq_name
                defaults['engineering_code']=seq_name
            else:
                id = existingIDs[0]
                PartNum=self.browse(cr, uid, id)
                defaults['name']=PartNum.name
                defaults['engineering_code']=PartNum.engineering_code
            return {'value': {'auto_code4': id4, 'name' : str(defaults['name']), 'engineering_code' : str(defaults['engineering_code'])}}            
        return {}

    def on_change_code4(self, cr, uid, id, auto_code1=False, auto_code2=False, auto_code3=False, auto_code4=False, comp_type=False):
        if auto_code1 and auto_code2 and auto_code3 and auto_code4 and comp_type:
            defaults={}
            thisMachine=self.pool.get('plm.number1').browse(cr, uid, auto_code1)
            thisMachineNum=self.pool.get('plm.number2').browse(cr, uid, auto_code2)
            thisGroup=self.pool.get('plm.number3').browse(cr, uid, auto_code3)
            thisProg=self.pool.get('plm.number4').browse(cr, uid, auto_code4)
            seq_name=thisMachine.name+thisMachineNum.name+thisGroup.name+thisProg.name
            existingIDs=self.search(cr, uid, [('name','=',seq_name),('comp_type','=',comp_type)])
            if not existingIDs:
                defaults['name']=seq_name
                defaults['engineering_code']=seq_name
            else:
                return {}
                id = existingIDs[0]
                PartNum=self.browse(cr, uid, id)
                defaults['name']=PartNum.name
                defaults['engineering_code']=PartNum.engineering_code
            return {'value': {'auto_code4': auto_code4, 'name' : str(defaults['name']), 'engineering_code' : str(defaults['engineering_code'])}}            
        return {}

    def on_change_code5(self, cr, uid, id, auto_code5=False, auto_code6=False):
        if auto_code5 and auto_code6:
            defaults={}
            thisCategory=self.pool.get('plm.number5').browse(cr, uid, auto_code5)
            thisType=self.pool.get('plm.number6').browse(cr, uid, auto_code6)
            nextNumb=self.pool.get('plm.number7')
            seq_name=thisCategory.name+thisType.name
            existingIDs=nextNumb.search(cr, uid, [('auto_code','=',seq_name)])
            if not existingIDs:
                if thisCategory.name[1]=='S':
                    defaults['name']="01"
                else:
                    defaults['name']="001"
                defaults['description']='Part Number'+seq_name
                defaults['auto_code']=seq_name
                defaults['category']=0
                id4=nextNumb.create(cr,uid,defaults)
            else:
                id4 = existingIDs[0]
                PartNum=nextNumb.browse(cr, uid, id4)
                defaults['category']=PartNum.category
                Progressive=int(PartNum.name)
                if thisCategory.name[1]=='S':
                    if Progressive<9:
                        defaults['name']="0"+str(Progressive+1)
                    elif Progressive<99:
                        defaults['name']=str(Progressive+1)
                    else:
                        return {}
                else:
                    if Progressive<9:
                        defaults['name']="00"+str(Progressive+1)
                    elif Progressive<99:
                        defaults['name']="0"+str(Progressive+1)
                    elif Progressive<999:
                        defaults['name']=str(Progressive+1)
                    else:
                        return {}

                nextNumb.write(cr,uid,id4,defaults)

            seq_name=seq_name+str(defaults['name'])
            existingIDs=self.search(cr, uid, [('name','=',seq_name)])
            if not existingIDs:
                defaults['name']=seq_name
                defaults['engineering_code']=seq_name
            else:
                id = existingIDs[0]
                PartNum=self.browse(cr, uid, id)
                defaults['name']=PartNum.name
                defaults['engineering_code']=PartNum.engineering_code
            return {'value': {'auto_code7': id4, 'name' : str(defaults['name']), 'engineering_code' : str(defaults['engineering_code']), 'category':str(defaults['category'])}}            
        return {}

    def on_change_code7(self, cr, uid, id, auto_code5=False, auto_code6=False, auto_code7=False):
        if auto_code5 and auto_code5 and auto_code7:
            defaults={}
            thisCategory=self.pool.get('plm.number5').browse(cr, uid, auto_code5)
            thisType=self.pool.get('plm.number6').browse(cr, uid, auto_code6)
            thisNumb=self.pool.get('plm.number7').browse(cr, uid, auto_code7)
            seq_name=thisCategory.name+thisType.name+thisNumb.name
            existingIDs=self.search(cr, uid, [('name','=',seq_name)])
            if not existingIDs:
                defaults['name']=seq_name
                defaults['engineering_code']=seq_name
            else:
                return {}
                id = existingIDs[0]
                PartNum=self.browse(cr, uid, id)
                defaults['name']=PartNum.name
                defaults['engineering_code']=PartNum.engineering_code
                defaults['category']=PartNum.category
            return {'value': {'name':str(defaults['name']), 'engineering_code':str(defaults['engineering_code']), 'category':str(defaults['category'])}}            
        return {}

    def on_change_code8(self, cr, uid, id, auto_code5=False, auto_code6=False, auto_code7=False, auto_code8=False):
        if auto_code5 and auto_code5 and auto_code7 and auto_code8:
            defaults={}
            thisCategory=self.pool.get('plm.number5').browse(cr, uid, auto_code5)
            thisType=self.pool.get('plm.number6').browse(cr, uid, auto_code6)
            thisNumb=self.pool.get('plm.number7').browse(cr, uid, auto_code7)
            thisVersion=self.pool.get('plm.number8').browse(cr, uid, auto_code8)
            seq_name=thisCategory.name+thisType.name+thisNumb.name+thisVersion.name
            existingIDs=self.search(cr, uid, [('name','=',seq_name)])
            if not existingIDs:
                defaults['name']=seq_name
                defaults['engineering_code']=seq_name
            else:
                return {}
                id = existingIDs[0]
                PartNum=self.browse(cr, uid, id)
                defaults['name']=PartNum.name
                defaults['engineering_code']=PartNum.engineering_code
            return {'value': {'name' : str(defaults['name']), 'engineering_code' : str(defaults['engineering_code'])}}            
        return {}

plm_component()

