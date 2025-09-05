# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PlmConversionStackLine(models.Model):
    _name = 'plm.conversion.stack.line'
    _description = 'PLM Conversion Stack Line'

    conversion_stack_id = fields.Many2one('plm.convert.stack', string='Stack', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', related="conversion_stack_id.product_id")
    attachment_id = fields.Many2one('ir.attachment', string='Attachment')
    model_id = fields.Many2one(
        'ir.model',
        string='Odoo Model',
        domain="[('model', 'in', ['product.product','ir.attachment'])]"
    )

    field_id = fields.Many2one(
        'ir.model.fields',
        string='Odoo Field',
        domain="[('model_id', '=', model_id)]"
    )

    old_value = fields.Char(string='Old Value')
    new_value = fields.Char(string='New Value')
    cad_field = fields.Char(string="Cad field", compute="_compute_cad_field")

    @api.depends('model_id', 'field_id')
    def _compute_cad_field(self):
        for line in self:
            mapping = self.env['odoo.cad.mapping'].search([
                ('odoo_model_id', '=', line.model_id.id),
                ('odoo_fields_id', '=', line.field_id.id)
            ], limit=1)
            line.cad_field = mapping.cad_field if mapping else False

    @api.onchange('product_id', 'model_id', 'field_id')
    def _onchange_old_value(self):

        for line in self:
            if line.product_id.id and line.field_id:
                product = self.env['product.product'].browse(line.product_id.id)
                field_name = line.field_id.name
                if field_name in product._fields:
                    line.old_value = str(product[field_name] or '')
