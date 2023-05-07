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
Created on 25 Apr 2023

@author: mboscolo
'''
import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProductTemplate (models.Model):
    _inherit = ['product.template']
    
    def before_move_to_state(self, from_state, to_state):
        """
        technical function for workflow customization
        :from_state state that came from
        :to_state state to go
        """
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx['active_id'] = self.product_variant_id.id
        ctx['active_model'] ='product.product'
        ctx['wf_action'] ='before'
        for action in self.env['plm.automatedwfaction'].search([('apply_to','=','product.product'),
                                                                ('from_state','=', from_state),
                                                                ('to_state','=', to_state),
                                                                ('before_after','=','before')]):
            action.with_context(ctx)._run()
        
        
    def after_move_to_state(self, from_state, to_state):
        """
        technical function for workflow customization
        :from_state state that came from
        :to_state state to go
        """
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx['active_id'] = self.product_variant_id.id
        ctx['active_model'] ='product.product'
        ctx['wf_action'] ='after'
        for action in self.env['plm.automatedwfaction'].search([('apply_to','=','product.product'),
                                                                ('from_state','=', from_state),
                                                                ('to_state','=', to_state),
                                                                ('before_after','=','after')]):
            action.with_context(ctx)._run()
