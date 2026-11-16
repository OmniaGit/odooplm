# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 25/mag/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
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
"""The conversion command of the documents: one wizard for the conversions
Odoo makes itself and the ones the CAD workstations make, the update to the
target CAD version and the conversion templates (predefined and personal).

The conversions are shown once each, whatever server their rule belongs to:
a conversion of a workstation goes into the queue and the first free
workstation that can make it takes it; a conversion of Odoo is made at once.
"""
import logging
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.plm_cad_agent_stack import CAD_VERSION_OPERATION, CONVERT_OPERATION
from ..models.plm_convert_template import normalize_extension
from ..models.plm_convert_workstation import EXPORT_MODES

_logger = logging.getLogger(__name__)

ODOO = "odoo"
WORKSTATION = "workstation"


class plm_temporary_batch_converter(models.TransientModel):
    _name = "plm.convert"
    _description = "Conversion Of Documents"

    def _default_document_ids(self):
        context = self.env.context
        if context.get("active_model") == "ir.attachment" and context.get("active_ids"):
            return [(6, 0, context["active_ids"])]
        if context.get("default_document_id"):
            return [(6, 0, [context["default_document_id"]])]
        return [(6, 0, [])]

    document_ids = fields.Many2many(
        "ir.attachment",
        "plm_convert_ir_attachment_rel",
        "wizard_id",
        "document_id",
        string="Documents",
        default=_default_document_ids,
    )
    template_id = fields.Many2one(
        "plm.convert.template",
        "Template",
        help="Chooses its conversions; the predefined ones are for everybody, the personal ones are yours.",
    )
    line_ids = fields.One2many("plm.convert.line", "wizard_id", "Conversions")
    cad_version_available = fields.Boolean(compute="_compute_cad_version_available")
    cad_version_update = fields.Boolean(
        "Update To The Target CAD Version",
        help="A CAD workstation opens the files and saves them in the target version of their CAD "
        "(PLM dictionaries, CAD Versions), without changing the history of the documents.",
    )
    template_name = fields.Char("Name Of My Template")

    def _extensions(self):
        return {os.path.splitext(document.name or "")[1].lower() for document in self.document_ids} - {""}

    @api.model
    def _available_formats(self, extensions):
        """The conversions that start from these extensions: the ones of Odoo
        (internal servers) and of the CAD workstations, enabled; not the CAD
        version updates (their own option)."""
        if not extensions:
            return self.env["plm.convert.format"]
        formats = self.env["plm.convert.format"].sudo().search(
            [
                ("available", "=", True),
                ("cad_version_update", "=", False),
                ("server_id.available", "=", True),
                "|",
                ("server_id.is_internal", "=", True),
                ("server_id.cad_agent", "=", True),
            ],
            order="id",
        )
        return formats.filtered(lambda f: normalize_extension(f.start_format) in extensions)

    @api.model
    def _cad_version_formats(self, extensions):
        """{extension: the CAD version update of that extension}."""
        out = {}
        formats = self.env["plm.convert.format"].sudo().search(
            [
                ("available", "=", True),
                ("cad_version_update", "=", True),
                ("server_id.available", "=", True),
                ("server_id.cad_agent", "=", True),
            ],
            order="id",
        )
        for convert_format in formats:
            extension = normalize_extension(convert_format.start_format)
            if extension in extensions:
                out.setdefault(extension, convert_format)
        return out

    @api.depends("document_ids")
    def _compute_cad_version_available(self):
        for wizard in self:
            wizard.cad_version_available = bool(wizard._cad_version_formats(wizard._extensions()))

    @api.onchange("document_ids")
    def _onchange_document_ids(self):
        """One line per conversion: the rule of a conversion made by hand
        (not presented by a workstation) is preferred, else the first."""
        stack = self.env["plm.convert.stack"]
        chosen = {}
        for convert_format in self._available_formats(self._extensions()):
            key = stack._conversion_key(convert_format)
            current = chosen.get(key)
            if not current or (current.presented and not convert_format.presented):
                chosen[key] = convert_format
        selected = {
            stack._conversion_key(line.format_id) for line in self.line_ids if line.selected and line.format_id
        }
        lines = [(5, 0, 0)]
        for key, convert_format in sorted(chosen.items(), key=lambda item: item[0][1:4] + item[0][:1]):
            lines.append(
                (
                    0,
                    0,
                    {
                        "format_id": convert_format.id,
                        "selected": key in selected,
                        "start_format": normalize_extension(convert_format.start_format),
                        "end_format": normalize_extension(convert_format.end_format),
                        "cad_name": convert_format.cad_name,
                        "cad_export_mode": convert_format.cad_export_mode,
                        "maker": WORKSTATION if convert_format.server_id.cad_agent else ODOO,
                    },
                )
            )
        self.line_ids = lines
        if self.template_id:
            self._apply_template()

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id:
            self._apply_template()

    def _apply_template(self):
        for line in self.line_ids:
            line.selected = self.template_id._matches(line)
        self.cad_version_update = self.template_id.cad_version_update and self.cad_version_available

    def _selected_formats(self):
        lines = self.line_ids.filtered("selected")
        return lines.mapped("format_id")

    def _cad_version_targets(self, formats_by_extension):
        targets = {}
        cads = self.env["plm.cad"].sudo()
        for convert_format in formats_by_extension.values():
            target = cads.get_target_version(convert_format.cad_name)
            if not target:
                raise UserError(
                    _(
                        "%s has no target version: choose it in PLM dictionaries, CAD Versions.",
                        convert_format.cad_name or convert_format.name,
                    )
                )
            targets[convert_format.id] = target
        return targets

    def action_convert(self):
        """Queue the jobs; the conversions of Odoo are made at once."""
        self.ensure_one()
        formats = self._selected_formats()
        if not formats and not self.cad_version_update:
            raise UserError(_("Choose at least one conversion."))
        if not self.document_ids:
            raise UserError(_("Choose at least one document."))
        stack = self.env["plm.convert.stack"]
        rows = stack._queue_jobs(self.document_ids, formats, CONVERT_OPERATION)
        rows.filtered(lambda row: not row.server_id.cad_agent).convert()
        if self.cad_version_update:
            update_formats = self._cad_version_formats(self._extensions())
            targets = self._cad_version_targets(update_formats)
            rows |= stack._queue_jobs(
                self.document_ids, stack.env["plm.convert.format"].browse(list(targets)), CAD_VERSION_OPERATION, targets
            )
        if not rows:
            raise UserError(
                _("Nothing to queue: the same jobs are already waiting, or the files are at the target CAD version.")
            )
        return stack._queue_action(rows)

    def action_create_coversion(self):
        """Convert to the shared folder of the server: only the conversions
        Odoo makes itself."""
        self.ensure_one()
        formats = self._selected_formats()
        if not formats:
            raise UserError(_("Choose at least one conversion."))
        if any(convert_format.server_id.cad_agent for convert_format in formats):
            raise UserError(_("Only the conversions made by Odoo go to the shared folder."))
        stack = self.env["plm.convert.stack"]
        for document in self.document_ids:
            for convert_format in formats.filtered(
                lambda f: normalize_extension(f.start_format) == os.path.splitext(document.name or "")[1].lower()
            ):
                row = stack.create(
                    {
                        "convrsion_rule": convert_format.id,
                        "start_document_id": document.id,
                        "operation_type": "TOSHARED",
                    }
                )
                row.convert()
        raise UserError(_("File Converted check the shared folder"))

    def action_save_template(self):
        """Keep the chosen conversions as a personal template."""
        self.ensure_one()
        lines = self.line_ids.filtered("selected")
        if not lines and not self.cad_version_update:
            raise UserError(_("Choose at least one conversion."))
        name = (self.template_name or "").strip()
        if not name:
            raise UserError(_("Give a name to the template."))
        self.template_id = self.env["plm.convert.template"].create(
            {
                "name": name,
                "owner_id": self.env.uid,
                "cad_version_update": self.cad_version_update,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "start_format": line.start_format,
                            "end_format": line.end_format,
                            "cad_export_mode": line.cad_export_mode or False,
                        },
                    )
                    for line in lines
                ],
            }
        )
        self.template_name = False
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "name": _("Convert File"),
        }


class PlmConvertLine(models.TransientModel):
    _name = "plm.convert.line"
    _description = "Conversion Offered By The Wizard"
    _order = "start_format, end_format, cad_export_mode"

    wizard_id = fields.Many2one("plm.convert", required=True, ondelete="cascade")
    selected = fields.Boolean("Make")
    format_id = fields.Many2one("plm.convert.format", "Conversion Rule", readonly=True)
    start_format = fields.Char("From", readonly=True)
    end_format = fields.Char("To", readonly=True)
    cad_name = fields.Char("CAD", readonly=True)
    cad_export_mode = fields.Selection(EXPORT_MODES, string="Export Mode", readonly=True)
    maker = fields.Selection(
        [(ODOO, "Odoo, at once"), (WORKSTATION, "CAD workstation, in the queue")],
        string="Made By",
        readonly=True,
    )
