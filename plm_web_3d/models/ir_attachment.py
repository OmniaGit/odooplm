# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2020 https://OmniaSolutions.website
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
import os
import logging
import urllib.parse

from odoo import api, fields, models

_logger = logging.getLogger(__name__)
SUPPORTED_WEBGL_EXTENTION = [
    ".3mf",
    ".gltf",
    ".glb",
    ".fbx",
    ".obj",
    ".wrl",
    ".json",
    ".stl",
    ".svg",
    ".dxf",
    ".stp",
    ".step",
]


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    has_web3d = fields.Boolean(
        string="Has 3d Web link",
        compute="_compute_web_3d_link",
        # store=True,
        help="Check if this document has related 3d web document",
    )
    web3d_part_colors = fields.Text(
        string="3D Part Colors",
        help="JSON map of part GUID to hex color, saved from the 3D viewer.",
    )

    def isWebGl(self):
        for ir_attachment in self:
            if ir_attachment.name:
                _name, exte = os.path.splitext(ir_attachment.name)
                return exte.lower() in SUPPORTED_WEBGL_EXTENTION
        return False

    @api.depends("name")
    def _compute_web_3d_link(self):
        attach_relations = self.env["ir.attachment.relation"]
        for ir_attachment in self:
            if ir_attachment.isWebGl():
                ir_attachment.has_web3d = True
                continue
            ir_attachment.has_web3d = attach_relations.search_count([
                ("parent_id", "=", ir_attachment.id),
                ("link_kind", "=", "Web3DTree")
            ])

    def get_url_for_3dWebModel(self):
        attach_relations = self.env["ir.attachment.relation"]
        for ir_attachment in self:
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            url_params = None
            if ir_attachment.isWebGl():
                url_params = urllib.parse.urlencode({
                    "document_id": ir_attachment.id,
                    "document_name": ir_attachment.name
                })
            else:
                for rel in attach_relations.search([
                    ("parent_id", "=", ir_attachment.id),
                    ("link_kind", "=", "Web3DTree")
                ]):
                    url_params = urllib.parse.urlencode({
                        "document_id": rel.child_id.id,
                        "document_name": rel.child_id.name
                    })
            if url_params:
                return f"{base_url}/plm/show_treejs_model?{url_params}"
    def _get_or_create_3mf_from_step(self):
        """Return existing 3MF conversion of this STEP file, creating it if needed."""
        self.ensure_one()
        # Look for an already-converted 3MF linked to this STEP
        if 'source_convert_document' in self._fields:
            existing = self.env['ir.attachment'].search([
                ('source_convert_document', '=', self.id),
                ('name', 'ilike', '.3mf'),
            ], limit=1)
            if existing:
                return existing
        # Perform conversion
        try:
            new_file_path = self.convert_from_step_to('.3mf')
        except Exception as e:
            _logger.error("STEP→3MF conversion failed for %s: %s", self.name, e)
            return self.env['ir.attachment']
        name_base, _ = os.path.splitext(self.name)
        with open(new_file_path, 'rb') as fh:
            data = base64.b64encode(fh.read())
        vals = {
            'name': name_base + '.3mf',
            'datas': data,
            'res_model': self.res_model,
            'res_id': self.res_id,
        }
        if 'is_converted_document' in self._fields:
            vals['is_converted_document'] = True
            vals['source_convert_document'] = self.id
        new_attachment = self.env['ir.attachment'].create(vals)
        if self.preview:
            new_attachment.preview = self.preview
        return new_attachment

    def show_releted_3d(self):
        for ir_attachment in self:
            _name, exte = os.path.splitext(ir_attachment.name or "")
            if exte.lower() in (".stp", ".step"):
                # Three.js cannot render STEP natively; convert to 3MF first
                target = ir_attachment._get_or_create_3mf_from_step()
            else:
                target = ir_attachment
            if not target:
                continue
            url = target.get_url_for_3dWebModel()
            if url:
                return {
                    "name": "Odoo TreeJs View",
                    "res_model": "ir.actions.act_url",
                    "type": "ir.actions.act_url",
                    "target": self,
                    "url": url,
                }

    def get_all_relation(self, document_id, exte):
        out = {}
        if exte in document_id.name:
            out[document_id.id] = document_id.name
        for child_attachment_id in self.getRelatedHiTree(document_id.id):
            if exte in self.browse(child_attachment_id).name:
                out[child_attachment_id.id] = child_attachment_id.name
        return out
