# -*- coding: utf-8 -*-

from odoo import models, fields

class PlmConversionStackLine(models.Model):
    _name = 'plm.conversion.stack.line'
    _description = 'PLM Conversion Stack Line'

    stack_id = fields.Many2one('plm.convert.stack', string='Stack', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    attachment_id = fields.Many2one('ir.attachment', string='Attachment')
    model_id = fields.Many2one('ir.model', string='Odoo Model')
    field_id = fields.Many2one('ir.model.fields', string='Odoo Field')
    old_value = fields.Char(string='Old Value')
    new_value = fields.Char(string='New Value')


