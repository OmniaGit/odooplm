# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<https://www.omniasolutions.website>).
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import base64
import requests
from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError


class ir_attachment(models.Model):
    _inherit = "ir.attachment"


    def action_update_checkout_flag(self):
        for rec in self:
            _docName, _docRev, chekOutUser, _hostName = self.env['ir.attachment'].getCheckedOut(rec.id, None)
            rec.is_checkout_flag = bool(chekOutUser)

    def action_fetch_cad_data(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        conversion_server_ip = IrConfig.get_param('conversion_server_ip',default='192.168.56.101')
        conversion_server_port = IrConfig.get_param('conversion_server_port')
        conversion_server_protocol = IrConfig.get_param('conversion_server_protocol', default='http')

        serverName = f"{conversion_server_protocol}://{conversion_server_ip}:{conversion_server_port}"
        url = f"{serverName}/odooplm/api/v1.0/get_properties"
        file_name = self.name
        binary_data = base64.b64decode(self.datas)

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
                ('attachment_id', '=', self.id)
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
                            to_update.append((existing_record['id'], {'value': evaluated_value}))
                        else:
                            to_create.append({
                                'name': conf_name,
                                'key': line.get('property_name'),
                                'value': evaluated_value,
                                'attachment_id': self.id
                            })
            if to_create:
                self.env['cad.config'].create(to_create)

            if to_update:
                for rec_id, vals in to_update:
                    self.env['cad.config'].browse(rec_id).write(vals)

    def action_open_cad_config(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'CAD Configurations',
            'res_model': 'cad.config',
            'view_mode': 'list',
            'domain': [('attachment_id', '=', self.id)],
            'target': 'current',
            'context': {'group_by': 'name'},
        }

    def open_ir_attachment_wizard_config(self):
        attachment_id = self.browse(self.env.context.get('active_id'))
        if not attachment_id.is_checkout:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Update Property Wizard',
                'res_model': 'update.property',
                'view_mode': 'form',
                'view_id': self.env.ref('plm_client_customprocedure.view_update_property_form').id,
                'target': 'new',
                'context': {
                    'default_attachment_id': self.env.context.get('active_id')
                },
            }
        else:
            raise ValidationError('Please check out before fetching the data.')
