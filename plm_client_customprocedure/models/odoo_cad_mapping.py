# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2022 https://OmniaSolutions.website
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
import base64
import os
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError


class OdooCadMapping(models.Model):
    _name = 'odoo.cad.mapping'
    _description = 'Odoo CAD Mapping'
    _sql_constraints = [
        ('validate_duplicate_model_field',
         'unique(odoo_model_id, odoo_fields_id)',
         'This field is already mapped for the model')
    ]

    odoo_model_id = fields.Many2one(
        'ir.model',
        string="Odoo Model",
        domain="[('model', 'in', ['product.product', 'ir.attachment'])]"
    )
    odoo_fields_id = fields.Many2one('ir.model.fields',  domain="[('model_id', '=', odoo_model_id)]")
    cad_field = fields.Char(string='Mapping')
