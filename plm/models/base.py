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
import json
import logging
from lxml import etree

from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from datetime import date
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

class Base(models.AbstractModel):
    _inherit = 'base'
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self.env.context.get('odooPLM'):
            return self.koo_fields_view_get(view_id, view_type, toolbar, submenu)
        raise NotImplemented("Function not available")

    @api.model
    def koo_fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        def sanitize(dict_from):
            return json.loads(json.dumps(dict_from, default=json_serial).replace("null", "false"))
        result = self.get_views([(view_id, view_type)], {'toolbar': toolbar, 'submenu': submenu})['views'][view_type]
        node = etree.fromstring(result['arch'])
        view_fields = set(el.get('name') for el in node.xpath('.//field[not(ancestor::field)]'))
        result['fields'] = self.fields_get(view_fields)
        result.pop('models', None)
        if 'id' in result:
            view = self.env['ir.ui.view'].sudo().browse(result.pop('id'))
            result['name'] = view.name
            result['type'] = view.type
            result['view_id'] = view.id
            #result['field_parent'] = view.field_parent
            result['base_model'] = view.model
        else:
            result['type'] = view_type
            result['name'] = 'default'
            #result['field_parent'] = False
        
        for key in ['arch', 'id', 'model', 'models', 'fields']:
            if key in result:
                result[key] = sanitize(result.get(key))    
        return result
            
        
        
        
        
        