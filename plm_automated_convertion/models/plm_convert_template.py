# -*- coding: utf-8 -*-
"""Conversion templates: several conversions chosen at once in the
conversion wizard. A template without owner is predefined, for everybody (made
by a Plm Convert Admin or loaded by a module); a template with an owner is a
personal one, made with "Save as my template" in the wizard."""
from odoo import api, fields, models

from .plm_convert_workstation import EXPORT_MODES


def normalize_extension(value):
    value = (value or "").strip().lower()
    if value and not value.startswith("."):
        value = "." + value
    return value


class PlmConvertTemplate(models.Model):
    _name = "plm.convert.template"
    _description = "Conversion Template"
    _order = "owner_id desc, sequence, name"

    name = fields.Char("Name", required=True, translate=True)
    sequence = fields.Integer("Sequence", default=10)
    active = fields.Boolean("Active", default=True)
    owner_id = fields.Many2one(
        "res.users",
        "Owner",
        index=True,
        ondelete="cascade",
        help="Empty: a predefined template, for everybody. Set: the personal template of this user.",
    )
    cad_version_update = fields.Boolean(
        "Update To The Target CAD Version",
        help="The files are also updated to the target version of their CAD (PLM dictionaries, CAD Versions).",
    )
    line_ids = fields.One2many("plm.convert.template.line", "template_id", "Conversions", copy=True)

    def _matches(self, line):
        """The wizard line is one of the conversions of this template."""
        self.ensure_one()
        return any(template_line._matches(line) for template_line in self.line_ids)


class PlmConvertTemplateLine(models.Model):
    _name = "plm.convert.template.line"
    _description = "Conversion Of A Template"
    _order = "start_format, end_format"

    template_id = fields.Many2one("plm.convert.template", "Template", required=True, ondelete="cascade", index=True)
    start_format = fields.Char("Start Format", required=True, help="The extension of the starting file, .ipt")
    end_format = fields.Char("End Format", required=True, help="The extension of the converted file, .step")
    cad_export_mode = fields.Selection(
        EXPORT_MODES,
        string="CAD Export Mode",
        help="Empty: whatever export mode the conversion has (a conversion made by Odoo has none).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            for name in ("start_format", "end_format"):
                if vals.get(name):
                    vals[name] = normalize_extension(vals[name])
        return super().create(vals_list)

    def write(self, vals):
        for name in ("start_format", "end_format"):
            if vals.get(name):
                vals[name] = normalize_extension(vals[name])
        return super().write(vals)

    def _matches(self, line):
        self.ensure_one()
        return (
            normalize_extension(line.start_format) == self.start_format
            and normalize_extension(line.end_format) == self.end_format
            and (not self.cad_export_mode or self.cad_export_mode == line.cad_export_mode)
        )
