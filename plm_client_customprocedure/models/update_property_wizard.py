# -*- coding: utf-8 -*-

import json
from odoo import models, fields, api
import base64
import os
import requests
from odoo.exceptions import UserError, ValidationError
from odoo import release
import re

# odoo version check #
current_version = release.version
match = re.match(r"(\d+)", current_version)
if match:
    major_version = match.group(1)
    print("Odoo major version:", major_version)
else:
    print("Could not parse version")


class UpdateProperty(models.Model):
    _name = 'update.property'
    _description = 'Update Property'

    attachment_id = fields.Many2one('ir.attachment', string='Attachment', required=True)
    cad_config_ids = fields.One2many('cad.config', 'update_property_id', string='Configuration')

    def action_fetch_cad_data(self):
        # conversion_wizard_id = False
        IrConfig = self.env['ir.config_parameter'].sudo()
        conversion_server_ip = IrConfig.get_param('conversion_server_ip')

        conversion_server_port = IrConfig.get_param('conversion_server_port')
        conversion_server_protocol = IrConfig.get_param('conversion_server_protocol', default='http')
        conversion_server_ip = conversion_server_ip
        conversion_server_port = conversion_server_port

        serverName = f"{conversion_server_protocol}://{conversion_server_ip}:{conversion_server_port}"

        url = f"{serverName}/odooplm/api/v1.0/get_properties"

        file_name = self.attachment_id.name
        binary_data = base64.b64decode(self.attachment_id.datas)
        files = {
            'file': (file_name, binary_data, 'application/octet-stream')
        }
        response = requests.post(url, files=files)
        if response.status_code == 200:
            try:
                result = response.json()
            except Exception as e:
                print("Failed to parse JSON:", e)
                raise UserError(f"Failed to parse response: {str(e)}")
            if not result:
                raise ValidationError('Not able to fetch file data')

            existing_records = self.env['cad.config'].search_read([
                ('attachment_id', '=', self.attachment_id.id)
            ], ['name', 'key', 'value'])
            existing_map = {
                (record['name'], record['key']): record
                for record in existing_records
            }
            to_update = []
            to_create = []
            for conf in result:
                conf_name = conf.get("name", False)
                config_data = conf.get('datas', [])
                if conf_name:
                    for line in config_data:
                        key = (conf_name, line.get('property_name'))
                        evaluated_value = line.get('evaluated_value')
                        if key in existing_map:
                            existing_record = existing_map[key]
                            to_update.append(
                                (existing_record['id'], {'value': evaluated_value, 'update_property_id': self.id}))
                        else:
                            to_create.append({
                                'name': conf_name,
                                'key': line.get('property_name'),
                                'value': evaluated_value,
                                'attachment_id': self.attachment_id.id,
                                'update_property_id': self.id,
                                'server_location': conf.get("server_location", False)

                            })

            if to_create:
                self.env['cad.config'].create(to_create)

            if to_update:
                for rec_id, vals in to_update:
                    self.env['cad.config'].browse(rec_id).write(vals)
        out = {
            "view_type": "form",
            "view_mode": "form",
            "res_model": "update.property",
            "view_id": self.env.ref("plm_client_customprocedure.view_update_property_form").id,
            "type": "ir.actions.act_window",
            "target": "new",
            "res_id": self.ids[0],
        }

        return out

    def update_cad_server_data(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        conversion_server_ip = IrConfig.get_param('conversion_server_ip')

        conversion_server_port = IrConfig.get_param('conversion_server_port')
        conversion_server_protocol = IrConfig.get_param('conversion_server_protocol', default='http')

        serverName = f"{conversion_server_protocol}://{conversion_server_ip}:{conversion_server_port}"
        url = f"{serverName}/odooplm/api/v1.0/update_properties"


        updated_lines = self.cad_config_ids.filtered(lambda c: c.is_updated)
        cad_data_update = {}
        for line in updated_lines:
            if line.name not in cad_data_update:
                cad_data_update[line.name] = []
            cad_data_update[line.name].append({line.key: line.value})
            cad_data_update['file_to_update'] = line.server_location
            cad_data_update['integration'] = 'solidworks'
            cad_data_update['current_version'] = major_version

        try:
            response = requests.post(
                url,
                json=cad_data_update,
                headers={'Content-Type': 'application/json'},
            )
        except Exception:
            raise ValidationError("Invalid license or expired")

        if response.status_code == 200:

            binary_data = response.content
            updated_lines.write({'is_updated': False})

            try:
                encoded_data = base64.b64encode(binary_data).decode('utf-8')
                self.attachment_id.write({
                    'datas': encoded_data,
                    'mimetype': 'application/octet-stream'
                })
                self.attachment_id.message_post(
                    body=f"File Update successful : {self.attachment_id.name}"
                )
            except Exception:
                raise ValidationError("File update failed during processing")
        else:
            try:
                error_msg = response.json().get("error", "Invalid license or expired")
            except Exception:
                error_msg = response.text or "Invalid license or expired"
            raise ValidationError(error_msg)

    def update_conversion_file_stack(self):
        """
        Check if there are updated configuration lines
        :return: None
        """
        updated_lines = self.cad_config_ids.filtered(lambda c: c.is_updated)
        if not updated_lines:
            return

        product_id = self.attachment_id.linkedcomponents.filtered(lambda p: p._name == 'product.product')[:1]

        line_vals = []
        mappings_data = self.env['odoo.cad.mapping'].search([])

        for line in updated_lines:

            mapping = mappings_data.filtered(lambda m: m.cad_field == line.key)
            cad_field = mapping.cad_field if mapping else line.key
            line_vals.append((0, 0, {
                'attachment_id': self.attachment_id.id,
                'model_id': mapping.odoo_model_id.id,
                'field_id': mapping.odoo_fields_id.id,
                'cad_field': cad_field,
                'old_value': line.old_value or '',
                'new_value': line.value or '',
            }))

        stack_vals = {
            'start_document_id': self.attachment_id.id,
            'operation_type': 'update_Cad',
            'conversion_line_ids': line_vals,
            'stack_data': {
                'data_to_update': [{line.key: line.value} for line in updated_lines]
            }
        }
        self.env['plm.convert.stack'].create(stack_vals)

        updated_lines.write({'is_updated': False})

        if self.attachment_id:
            self.attachment_id.linkedcomponents.write({'update_3d_file': True})
