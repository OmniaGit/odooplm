# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2026 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
import os

from odoo import fields, models


class PackGoExportType(models.Model):
    _name = "plm.pack.go.export.type"
    _description = "Pack and Go export type"
    _order = "sequence, id"

    name = fields.Char("Name", required=True, translate=True)
    sequence = fields.Integer("Sequence", default=10)
    active = fields.Boolean("Active", default=True)
    include_2d = fields.Boolean("2D", help="Export the 2D documents")
    include_pdf = fields.Boolean(
        "PDF",
        help="Export the printouts of the 2D documents and the PDF files",
    )
    include_3d = fields.Boolean("3D", help="Export the 3D documents")
    include_other = fields.Boolean(
        "Other",
        help="Export the documents that are neither 2D, 3D nor PDF",
    )
    extension_ids = fields.Many2many(
        "plm.pack.go.extension",
        relation="plm_pack_go_export_type_extension_rel",
        column1="export_type_id",
        column2="extension_id",
        string="Extensions",
        help="When set, only the files with one of these extensions are exported."
        " The printouts of the 2D documents are not filtered.",
    )

    def _plm_accepts_file(self, file_name):
        """True when the extension filter lets the file through."""
        self.ensure_one()
        if not self.extension_ids:
            return True
        extension = os.path.splitext(file_name or "")[1].lower()
        return extension in self.extension_ids.mapped("name")
