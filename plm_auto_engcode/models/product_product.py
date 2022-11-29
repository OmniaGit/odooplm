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

class pProductProduct(models.Model):
    _inherit = 'product.product'
    
    @api.onchange("categ_id")
    def onchange_categ_id(self):
        if not self.id.origin:
            eng_code = self.product_tmpl_id._getNewCode()
            self.engineering_code = eng_code
            self.product_tmpl_id.engineering_code = eng_code
                
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _getNewCode(self):
        if self.env.context.get('odooPLM', False):
            if self.categ_id and self.categ_id.plm_code_sequence:
                return self.categ_id.plm_code_sequence.next_by_id()
            return self.env['ir.sequence'].next_by_code('plm.eng.code')
        return False
    
    @api.onchange("categ_id")
    def onchange_categ_id(self):
        if self.id.origin:
            self.engineering_code = self._getNewCode()
        
    engineering_code = fields.Char(_('Part Number'),
                                   index=True,
                                   help=_("This is engineering reference to manage a different P/N from item Name."),
                                   size=64)
