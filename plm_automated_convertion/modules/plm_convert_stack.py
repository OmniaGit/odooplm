# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
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
Created on Sep 7, 2019

@author: mboscolo
'''
from odoo import models
from odoo import fields
from odoo import api


class PlmConvertStack(models.Model):
    _name = "plm.convert.stack"
    _description = "Stack of conversions"
    _order = 'sequence ASC'

    sequence = fields.Integer('Sequence')
    start_format = fields.Char('Start Format')
    end_format = fields.Char('End Format')
    product_category = fields.Many2one('product.category', 'Category')
    conversion_done = fields.Boolean('Conversion Done')
    start_document_id = fields.Many2one('ir.attachment', 'Starting Document')
    end_document_id = fields.Many2one('ir.attachment', 'Converted Document')
    output_name_rule = fields.Char('Output Name Rule')
    
    def setToConvert(self):
        for convertStack in self:
            convertStack.conversion_done = False

    @api.model
    def create(self, vals):
        ret = super(PlmConvertStack, self).create(vals)
        if not vals.get('sequence'):
            ret.sequence = ret.id
        return ret

