# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 03/nov/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
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
from odoo import _, fields, models
import json


class ProductProduct(models.Model):
    _inherit = "product.product"

    update_3d_file = fields.Boolean(string='Update 3D File')
    mapping_id = fields.Many2one('odoo.cad.mapping')
    product_change_values = fields.Text()

    def write(self, vals):
        tracked_fields = self.env['odoo.cad.mapping'].search([]).mapped('odoo_fields_id.name')

        for record in self:
            changes = []
            for field in tracked_fields:
                if field in vals:
                    old_val = getattr(record, field)
                    new_val = vals.get(field)
                    if old_val != new_val:
                        changes.append({
                            'field': field,
                            'old': old_val,
                            'new': new_val
                        })
            if changes:
                record.product_change_values = json.dumps(changes)
                record.update_3d_file = True

        return super().write(vals)

    def _cron_auto_create_plm_convert_stack(self):
        """
        This cron action will automatically create plm convert stack
        record base of boolean(update_3d_file) on product model.
        """
        products_to_update = self.search([('update_3d_file', '=', True)])
        Stack = self.env['plm.convert.stack'].sudo()

        for product in products_to_update:
            attachment_id = product.linkeddocuments.filtered(lambda a: a.document_type == "3d")

            existing_stack = Stack.search([
                ('start_document_id', '=', attachment_id.id),
                ('state', '=', 'draft')
            ])
            if existing_stack:
                continue

            field_changes = json.loads(product.product_change_values or "[]")
            line_vals = []
            for change in field_changes:
                mapping = self.env['odoo.cad.mapping'].search([
                    ('odoo_fields_id.name', '=', change['field'])
                ])
                cad_field = mapping.cad_field if mapping else change['field']

                line_vals.append((0, 0, {
                    'product_id': product.id,
                    'attachment_id': attachment_id.id,
                    'model_id': mapping.odoo_model_id.id,
                    'field_id': mapping.odoo_fields_id.id,
                    'cad_field': cad_field,
                    'old_value': change['old'] or '',
                    'new_value': change['new'] or '',
                }))

            Stack.create({
                'start_document_id': attachment_id.id,
                'operation_type': 'update_Cad',
                'conversion_line_ids': line_vals
            })
            product.write({'update_3d_file': False})

    def forceRecursiveConvert(self, recursive=True):
        convert_stacks = self.env["plm.convert.stack"]
        for product in self:
            document_ids = []
            for document in product.linkeddocuments:
                if recursive:
                    document_ids.extend(
                        document.getRelatedAllLevelDocumentsTree(document)
                    )
                else:
                    document_ids.append(document.id)
            convert_stacks = (
                self.env["ir.attachment"]
                .browse(list(set(document_ids)))
                .generateConvertedFiles()
            )
        return {
            "name": _("Convert Stack"),
            "res_model": "plm.convert.stack",
            "view_type": "form",
            "view_mode": "list,form",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", convert_stacks.ids)],
            "context": {},
        }
