# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2023 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''
Created on 24 Apr 2023

@author: mboscolo
'''
import json
import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.plm.models.plm_mixin import USED_STATES
    

class PlmAutomatedWFAction(models.Model):
    _name ='plm.automatedwfaction'
    _description = "Plm Automated Work Flow Actions"
    name = fields.Char("Action Name")
    from_state = fields.Selection(USED_STATES,
                                  string="From Stare")
    to_state = fields.Selection(USED_STATES,
                                string ="To State")
    before_after = fields.Selection([('before','Before'),
                                     ('after', 'After')],
                                     string="Perform",
                                     help="you can choose to perform the action before or after the workflow action")
    
    apply_to = fields.Selection([('product.product','Product'),
                                 ('ir.attachment', 'Attachment')],
                                 string="Apply To",
                                 help="Apply this action to the workflow model")
    
    domain = fields.Char("Domain", help="""specifie the domain of the action""")

    child_ids = fields.Many2many('ir.actions.server',
                                 'rel_plm_server_actions',
                                 'server_id',
                                 'action_id',
                                 string='Child Actions', 
                                 help='Child server actions that will be executed. Note that the last return returned action value will be used as global return value.')
    def name_get(self):
        out=[]
        for o in self:
            out.append((o.id,"[%s | %s] %s" % (o.to_state, o.before_after, o.name or '')))
        return out 
    
    def _run(self):
        res = False
        active_id = self.env.context['active_id']
        active_model = self.env.context['active_model']
        if active_model ==self.apply_to:
            base_domain = [('id', '=', active_id)]
            for act in self.child_ids.sorted():
                if self.domain:
                    base_domain = base_domain + json.loads(self.domain.replace("\'",""))
                    obj_id = self.env[active_model].search(base_domain)
                else:
                    obj_id = self.env[active_model].browse(active_id)
                if obj_id:
                    res = act.run() or res
        return res
        
    
    
    
    
    