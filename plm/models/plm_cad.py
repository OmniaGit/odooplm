##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2026 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
"""The CADs the PLM works with, their versions, and the version each CAD is
updated to (the target of a CAD version update)."""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PlmCad(models.Model):
    _name = "plm.cad"
    _description = "PLM CAD"
    _order = "sequence, name"

    name = fields.Char("Name", required=True)
    code = fields.Char(
        "Code",
        required=True,
        help="The CAD name the CAD clients send (CAD_NAME), kept in the Cad Name of the documents.",
    )
    prog_id = fields.Char(
        "COM ProgID",
        help="The COM ProgID the CAD application registers on Windows (Inventor.Application): "
        "it tells whether the CAD is installed on a computer.",
    )
    sequence = fields.Integer("Sequence", default=10)
    active = fields.Boolean("Active", default=True)
    version_ids = fields.One2many("plm.cad.version", "cad_id", string="Versions")
    target_version_id = fields.Many2one(
        "plm.cad.version",
        string="Target Version",
        domain="[('cad_id', '=', id)]",
        help="The version the files of this CAD are updated to by a CAD version update.",
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "A CAD with this code exists already."),
    ]

    @api.constrains("target_version_id")
    def _check_target_version(self):
        for cad in self:
            if cad.target_version_id and cad.target_version_id.cad_id != cad:
                raise ValidationError(_("The target version of %s must be one of its versions.", cad.name))

    @api.model
    def find_cad(self, cad_name):
        """The CAD of a CAD name, as the documents (code) or the conversion
        rules (name) write it, whatever the case; an empty record when unknown."""
        cad_name = (cad_name or "").strip()
        if not cad_name:
            return self.browse()
        return self.search(["|", ("code", "=ilike", cad_name), ("name", "=ilike", cad_name)], limit=1)

    @api.model
    def get_target_version(self, cad_name):
        """The target version of a CAD name (Inventor, INVENTOR), False when the
        CAD is unknown or has no target."""
        return self.find_cad(cad_name).target_version_id.name or False


class PlmCadVersion(models.Model):
    _name = "plm.cad.version"
    _description = "PLM CAD Version"
    _order = "cad_id, sequence desc, name desc"

    cad_id = fields.Many2one("plm.cad", string="CAD", required=True, ondelete="cascade", index=True)
    name = fields.Char(
        "Version",
        required=True,
        help="The version as its CAD names it (2025, 12.0, 1.1): the CAD Version a document gets once updated.",
    )
    sequence = fields.Integer("Sequence", help="Orders the versions of a CAD: the newest has the highest.")
    active = fields.Boolean("Active", default=True)

    _sql_constraints = [
        ("cad_name_unique", "unique(cad_id, name)", "This version of the CAD exists already."),
    ]

    @api.depends("cad_id.name", "name")
    def _compute_display_name(self):
        for version in self:
            version.display_name = "%s %s" % (version.cad_id.name or "", version.name or "")
