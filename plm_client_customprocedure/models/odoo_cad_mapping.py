# -*- coding: utf-8 -*-
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
