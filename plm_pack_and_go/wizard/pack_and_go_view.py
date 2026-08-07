# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
"""
Created on Mar 30, 2016

@author: Daniel Smerghetto
"""
import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AdvancedPackView(models.TransientModel):
    _name = "pack_and_go_view"
    _description = "Manage pack view for exporting"

    component_id = fields.Many2one("product.template", "Component")
    document_id = fields.Many2one("ir.attachment", "Document")
    comp_rev = fields.Integer("Component Revision")
    comp_description = fields.Char(compute="_getComponentDescription")
    doc_rev = fields.Integer("Document Revision")
    document_description = fields.Char(compute="_getDocumentDescription")
    doc_file_name = fields.Char(compute="_getDocumentFileName")
    preview = fields.Binary("Preview Content")
    # Don't change keys because are used in a lower check in this file
    doc_type = fields.Selection(
        [
            ("2d", "2D"),
            ("3d", "3D"),
            ("other", "Other"),
            ("pdf", "PDF"),
        ],
        "Document Type",
    )
    available_types = fields.Many2one("pack_and_go_types", "Types")
    pack_and_go_id = fields.Many2one("pack.and_go", "Pack and go id")


    @api.model
    def _getComponentDescription(self):
        for row in self:
            row.comp_description = row.component_id.name

    @api.model
    def _getDocumentDescription(self):
        for row in self:
            row.document_description = row.document_id.name

    @api.model
    def _getDocumentFileName(self):
        for row in self:
            row.doc_file_name = row.document_id.name

