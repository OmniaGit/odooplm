# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<https://www.omniasolutions.website>).
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
