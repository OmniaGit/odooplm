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
import base64
import logging
import traceback
import requests
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import release
import re

from odoo import models, fields

current_version = release.version
match = re.match(r"(\d+)", current_version)
if match:
    major_version = match.group(1)
else:
    print("Could not parse version")


class PlmConvertStack(models.Model):
    _inherit = "plm.convert.stack"  # inherit existing model

    conversion_line_ids = fields.One2many(
        comodel_name='plm.conversion.stack.line',
        inverse_name='conversion_stack_id',
        string='Changes'
    )

    def _auto_update_cad_file(self):

        IrConfig = self.env['ir.config_parameter'].sudo()
        conversion_server_ip = IrConfig.get_param('conversion_server_ip')
        conversion_server_port = IrConfig.get_param('conversion_server_port')
        conversion_server_protocol = IrConfig.get_param('conversion_server_protocol', default='http')
        conversion_server_ip = conversion_server_ip
        conversion_server_port = conversion_server_port

        serverName = f"{conversion_server_protocol}://{conversion_server_ip}:{conversion_server_port}"
        url = f"{serverName}/odooplm/api/v1.0/update_odoo_mapping_cad_properties"

        mappings_data = self.env['odoo.cad.mapping'].search([])

        cad_update_data = {}
        data_to_update = []
        if self.stack_data:
            data_to_update = self.stack_data['data_to_update']
        else:
            pass
        for line in self.conversion_line_ids:
            cad_field = mappings_data.filtered(lambda a: a.odoo_fields_id.name == line.field_id.name).cad_field
            data_to_update.append({cad_field: line.new_value or line.old_value})

        cad_update_data['data_to_update'] = data_to_update
        cad_update_data['file_content'] = (self.start_document_id.datas).decode('utf-8')
        cad_update_data['integration'] = 'solidworks'
        cad_update_data['file_name'] = self.start_document_id.name
        cad_update_data['current_version'] = major_version

        self.start_document_id.toggle_check_out()
        response = requests.post(url, json=cad_update_data, headers={'Content-Type': 'application/json'})
        if response.status_code != 200:
            try:
                error_msg = response.json().get("error", response.text)
            except Exception:
                error_msg = response.text or "Invalid license or expired"
            return False, error_msg

        try:
            binary_data = response.content
            encoded_data = base64.b64encode(binary_data).decode('utf-8')
            self.start_document_id.write({
                'datas': encoded_data,
                'mimetype': 'application/octet-stream'
            })

            self.start_document_id.toggle_check_out()
            self.start_document_id.linkedcomponents.write({'update_3d_file': False})

            attachments_3d = self.start_document_id.linkedcomponents.linkeddocuments.filtered(
                lambda att: att.document_type == '3d'
            )
            attachment_name = ', '.join(attachments_3d.mapped('name'))
            if attachment_name:
                for product in self.start_document_id.linkedcomponents:
                    product.message_post(body=f'Product CAD file {attachment_name} update successful.')
                self.start_document_id.message_post(
                    body=f'CAD file {attachment_name} successfully updated and attached.'
                )
            return True, ""  # ✅ Success

        except Exception as e:
            # only triggered if license was valid but internal CAD update failed
            return False, f"Failed to process CAD update: {e}"

    def convert(self):
        for stack_id in self:
            if stack_id.operation_type == "update_Cad":
                try:
                    success, error_msg = stack_id._auto_update_cad_file()
                    if success:
                        stack_id.setToConverted()
                        stack_id.error_string = ""
                        self.env.cr.commit()
                    else:
                        stack_id.write({
                            'error_string': error_msg,
                            'state': 'draft'
                        })
                        continue  # skip success flow
                except Exception as ex:
                    logging.error(ex)
                    traceback.print_exc()
                    stack_id.error_string = (
                        _("Internal Error %s check odoo log for the full error stack") % ex
                    )
            else:
                super().convert()
