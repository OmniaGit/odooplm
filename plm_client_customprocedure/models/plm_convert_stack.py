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
"""
Created on Sep 7, 2019

@author: mboscolo
"""
import base64
import logging
import os
import shutil
import traceback
import requests
import tempfile
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import release
import re


# odoo version check #
current_version = release.version
match = re.match(r"(\d+)", current_version)
if match:
    major_version = match.group(1)
else:
    print("Could not parse version")


class PlmConvertStack(models.Model):
    _name = "plm.convert.stack"
    _description = "Stack of conversions"
    _order = "sequence ASC"

    name = fields.Char("Name", compute="_compute_name")
    sequence = fields.Integer(string="Sequence")
    convrsion_rule = fields.Many2one(
        "plm.convert.format", string="Conversion rule"
    )
    product_category = fields.Many2one("product.category", string="Category")
    conversion_done = fields.Boolean(string="Conversion Done")
    product_id = fields.Many2one('product.product', string='Product')
    start_document_id = fields.Many2one(
        "ir.attachment",
        string="Starting Document",
        domain=[("document_type", "=", "3d")],
        required=True
    )
    end_document_id = fields.Many2one("ir.attachment", string="Converted Document")
    output_name_rule = fields.Char("Output Name Rule")
    error_string = fields.Text("Error")
    server_id = fields.Many2one(
        related="convrsion_rule.server_id", string="Conversion Server"
    )
    operation_type = fields.Selection(
        [("UPDATE", "Update"), ("TOSHARED", "Shared Folder"), ("CONVERT", "Convert"), ("update_Cad", "Update Cad")],
        string="Operation Type",
        help="""
        Type of conversion operation
        Update: Perform an update to the given document (pdf, Bitmap)
        Download: Perform a conversion on the given format and download the file
                  in the given server path
        Convert: Convert the file in place on the stack object
        """
    )
    stack_data = fields.Json()
    conversion_line_ids = fields.One2many('plm.conversion.stack.line',
                                          'conversion_stack_id', string='Changes')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('done', 'Done'),
        ],
        string="Status",
        default='draft'
    )

    def _compute_name(self):
        for stack_id in self:
            stack_id.name = "%s: %s" % (
                stack_id.operation_type,
                stack_id.start_document_id.name,
            )

    def setToConver(self):
        for convertStack in self:
            convertStack.state = 'draft'

    def setToConverted(self):
        for convertStack in self:
            convertStack.state = 'done'

    @api.model_create_multi
    def create(self, vals):
        ret = super().create(vals)
        for r in ret:
            r.sequence = r.id
        return ret

    def getFileConverted(self, newFileName=False):
        targetExtention = self.convrsion_rule.end_format
        cadExange_path = self.env.ref("plm_automated_convertion.odoo_cadexcange")
        if self.server_id.is_internal:
            return self.start_document_id.convert_to_format(
                targetExtention, cadExange_path.value
            )
        else:
            # questa e sbagliata deve prendere il server che e' configurato

            # serverName = self.env["ir.config_parameter"].get_param(
            #     "plm_convetion_server"
            # )
            IrConfig = self.env['ir.config_parameter'].sudo()
            conversion_server_ip = IrConfig.get_param('conversion_server_ip')

            conversion_server_port = IrConfig.get_param('conversion_server_port')

            serverName = f"{conversion_server_ip}:{conversion_server_port}"
            if not serverName:
                raise Exception(

                    "Configure plm_convetion_server to use this functionality"
                )

            if not serverName:
                raise Exception(

                    "Configure plm_convetion_server to use this functionality"
                )


            url = "http://%s/odooplm/api/v1.0/saveas" % serverName
            params = {}
            params["targetExtention"] = targetExtention
            params["integrationName"] = self.convrsion_rule.cad_name

            response = requests.post(
                url, params=params, files=self.getAllFiles(self.start_document_id)
            )

            if response.status_code != 200:
                raise UserError(
                    "Conversion of cad server failed, check the cad server log"
                )
            if not newFileName:
                newFileName = self.start_document_id.name + targetExtention
            newTarget = os.path.join(tempfile.gettempdir(), newFileName)
            with open(newTarget, "wb") as f:
                f.write(response.content)
            return newTarget

    def _generateFile(self):
        document = self.start_document_id
        components = document.linkedcomponents.sorted(
            lambda line: line.engineering_revision
        )
        component = self.env["product.product"]
        if components:
            component = components[0]
        file_name = "%s_%s" % (document.name, document.engineering_revision)
        if self.output_name_rule:
            try:
                file_name = eval(
                    self.output_name_rule,
                    {"component": component, "document": document, "env": self.env},
                )
            except Exception as ex:
                raise Exception(
                    _("Cannot evaluate rule %s due to error %r") % (file_name, ex)
                )
        newFileName = file_name + self.convrsion_rule.end_format
        newFilePath = self.getFileConverted(newFileName)
        if not os.path.exists(newFilePath):
            raise Exception(_("File not converted"))
        return newFilePath

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
            if stack_id.state == 'done':
                continue
            try:
                if stack_id.operation_type == "UPDATE":
                    stack_id.start_document_id._updatePreview()
                elif stack_id.operation_type in "TOSHARED":
                    file_converted = stack_id._generateFile()
                    if stack_id.server_id.folder_to:
                        dest_path = os.path.join(
                            stack_id.server_id.folder_to,
                            os.path.basename(file_converted),
                        )
                        shutil.copyfile(file_converted, dest_path)
                    else:
                        raise Exception(
                            _("No server path defined for server %s" % stack_id.server_id.name)
                        )
                elif stack_id.operation_type == "CONVERT":
                    file_converted = stack_id._generateFile()
                    stack_id._attach_to_stack(file_converted)

                elif stack_id.operation_type == "update_Cad":
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

                else:
                    continue  # unknown operation, just skip

                stack_id.setToConverted()
                stack_id.error_string = ""
                self.env.cr.commit()
                stack_id.start_document_id.toggle_check_out()

            except Exception as ex:
                logging.error(ex)
                traceback.print_exc()
                stack_id.error_string = (
                    _("Internal Error %s check odoo log for the full error stack") % ex
                )

    def generateConvertedDocuments(self):
        logging.info("generateConvertedDocuments started")
        toConvert = self.search([("state", "=", 'draft')], order="sequence ASC")
        toConvert.convert()

    def getAllFiles(self, document_id):
        out = {}
        document = self.start_document_id
        ir_attachment = self.env["ir.attachment"]
        fileStoreLocation = ir_attachment._get_filestore()

        def get_file_content(doc):
            file_path = os.path.join(fileStoreLocation, doc.store_fname)
            if not os.path.exists(file_path):
                if doc.datas:
                    temp_path = os.path.join(tempfile.gettempdir(), doc.name)
                    with open(temp_path, "wb") as f:
                        f.write(base64.b64decode(doc.datas))
                    return open(temp_path, "rb")
                else:
                    raise UserError(_("Missing file in filestore and no in-database content for '%s'") % doc.name)
            return open(file_path, "rb")

        def templateFile(docId):
            doc = ir_attachment.browse(docId)
            return {doc.name: (doc.name, get_file_content(doc))}

        # Load root file
        out["root_file"] = (document.name, get_file_content(document))

        # Load all related files
        request = (document.id, [], -1, None, None)

        for outId, *_ in ir_attachment.CheckAllFiles(request):
            if outId == document.id:
                continue
            out.update(templateFile(outId))

        return out

    def _attach_to_stack(self, file_name):
        attachment = self.env["ir.attachment"]
        target_attachment = self.env["ir.attachment"]
        attachment_ids = attachment.search([("name", "=", file_name)])
        content = ""
        logging.info("Reading converted file %r" % (file_name))
        if not os.path.exists(file_name):
            raise Exception(_("Cannot find file %r") % (file_name))
        with open(file_name, "rb") as fileObj:
            content = fileObj.read()
        if content:
            logging.info(
                "File size %r, content len %r"
                % (os.path.getsize(file_name), len(content))
            )
            encoded_content = base64.b64encode(content)
            if attachment_ids:
                attachment_ids.write(
                    {"datas": encoded_content, "source_convert_document": self.start_document_id.id}
                )
                target_attachment = attachment_ids[0]
            else:
                target_attachment = attachment.create(
                    {
                        "linkedcomponents": [
                            (6, False, self.start_document_id.linkedcomponents.ids)
                        ],
                        "name": os.path.basename(file_name),
                        "datas": encoded_content,
                        "engineering_state": self.start_document_id.engineering_state,
                        "is_plm": True,
                        "engineering_code": file_name,
                        "is_converted_document": True,
                        "source_convert_document": self.start_document_id.id,
                    }
                )
            try:
                os.remove(file_name)
                logging.info("Removed file %r" % (file_name))
            except Exception as ex:
                logging.warning(ex)
        else:
            raise Exception(
                _("Cannot convert document %r because no content is provided."
                  "Convert stack %r")
                % (self.start_document_id.id, self.id)
            )
        self.end_document_id = target_attachment.id

    logging.debug("generateConvertedDocuments ended")
