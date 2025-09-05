# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class CadConfig(models.Model):
    _name = "cad.config"
    _description = "Cad Configurations"

    name = fields.Char("Configuration Name", required=True)
    key = fields.Char("Property")
    value = fields.Char("Value")
    old_value = fields.Char()
    attachment_id = fields.Many2one("ir.attachment", string="Attachment")
    update_property_id = fields.Many2one('update.property')
    server_location = fields.Char()
    integration = fields.Char()
    is_updated = fields.Boolean()

    @api.onchange('value')
    def _onchange_is_updated(self):
        for rec in self:
            rec.is_updated = True

    def write(self, vals):
        if 'value' in vals:
            for rec in self:
                rec.old_value = rec.value
        return super().write(vals)
