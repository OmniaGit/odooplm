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


class PlmConvertRule(models.Model):
    _name = "plm.convert.rule"
    _description = "Rule of conversions"

    start_format = fields.Char('Start Format')
    end_format = fields.Char('End Format')
    product_category = fields.Many2one('product.category', 'Category')
    server_id = fields.Many2one('plm.convert.servers', 'Conversion Server')
    output_name_rule = fields.Char('Output Name Rule', default="'%s_%s' % (document.name, document.revisionid)")
    convert_alone_documents = fields.Boolean('Convert documents without component', default=False)

