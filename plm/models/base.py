# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2020 https://OmniaSolutions.website
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
Created on 17 Nov 2020

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
import json
    
class Base(models.AbstractModel):
    _inherit = 'base'
    
    
    @api.model
    def koo_fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        def sanitize(dict_from):
            return json.loads(json.dumps(dict_from).replace("null", "false"))
        f = self.fields_view_get(view_id, view_type, toolbar, submenu)
        for key in ['field_parent', 'name', 'type', 'view_id', 'base_model', 'fields', 'toolbar']:
            if key in f:
                f[key] = sanitize(f.get(key))    
        return f
            
        
        
        
        
        