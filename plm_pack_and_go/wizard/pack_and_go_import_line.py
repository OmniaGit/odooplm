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
from odoo import fields, models


class PackAndGoImportLine(models.TransientModel):
    _name = "pack.and.go.import.line"
    _description = "Preview row of a Pack and Go import"

    import_id = fields.Many2one(
        "pack.and.go.import", string="Import", required=True, ondelete="cascade"
    )
    document_id = fields.Many2one("ir.attachment", string="Document")
    component_id = fields.Many2one("product.template", string="Component")
    doc_rev = fields.Integer(string="Revision")
    doc_type = fields.Selection(
        [("2d", "2D"), ("3d", "3D"), ("other", "Other")], string="Type"
    )
    status = fields.Selection(
        [
            ("changed", "Changed"),
            ("unchanged", "Unchanged"),
            ("not_checked_out", "Not checked out by you"),
            ("no_file", "No matching file in zip"),
        ],
        string="Status",
        help="A document no longer in Odoo also lands on no_file: either "
        "way, nothing will be imported for it; see Detail.",
    )
    message = fields.Char(string="Detail")
