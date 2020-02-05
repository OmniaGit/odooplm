##############################################################################
#
#    OmniaSolutions, Open Source Management Solution    
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
"""
Created on Mar 30, 2016

@author: Daniel Smerghetto
"""
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
import logging

    
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _getNewCode(self):
        if self.env.context.get('odooPLM', False):
           return self.env['ir.sequence'].next_by_code('plm.eng.code')        
        return False
    
    engineering_code = fields.Char(_('Part Number'),
                                   index=True,
                                   default = _getNewCode,
                                   help=_("This is engineering reference to manage a different P/N from item Name."),
                                   size=64)
