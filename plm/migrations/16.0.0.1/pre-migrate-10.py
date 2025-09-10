# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2024 https://OmniaSolutions.website
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
Created on 19 Jul 2024

@author: mboscolo
'''
import logging
from odoo.upgrade.util.fields import rename_field

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    rename_field(cr,
                 'product.template',
                 'state',
                 'engineering_state',
                 update_references=True,
                 domain_adapter=None, 
                 skip_inherit=())
    
    rename_field(cr,
                 'ir.attachment',
                 'state',
                 'engineering_state',
                 update_references=True,
                 domain_adapter=None, 
                 skip_inherit=())
    
    
    
    