# -*- coding: utf-8 -*-
"""Add the conversions of a template to a server: the rules the template
names and the server does not have yet are made, in Odoo, by a Plm Convert
Admin. A template only chooses rules in the conversion wizard; it does not
make them."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PlmConvertServersTemplateWizard(models.TransientModel):
    _name = "plm.convert.servers.template.wizard"
    _description = "Add Conversions From A Template"

    server_id = fields.Many2one("plm.convert.servers", "Server", required=True, ondelete="cascade")
    template_id = fields.Many2one("plm.convert.template", "Template", required=True, ondelete="cascade")
    cad_name = fields.Char(
        "CAD",
        required=True,
        help="The CAD of the conversions made, as the rules write it (Inventor).",
    )

    @api.onchange("server_id")
    def _onchange_server_id(self):
        """The CAD the workstation presented, else the CAD of its rules."""
        if self.cad_name or not self.server_id:
            return
        names = self.server_id.workstation_cad_ids.mapped("cad_name") or self.server_id.available_format.mapped(
            "cad_name"
        )
        self.cad_name = names[0] if names else False

    def _export_mode(self, line):
        """A conversion of a workstation needs an export mode: a template line
        without one makes a conversion to one file."""
        if line.cad_export_mode:
            return line.cad_export_mode
        return "file" if self.server_id.cad_agent else False

    def action_add(self):
        """Make the rules of the template the server does not have; a rule
        already there is made available again. Returns the rules made."""
        self.ensure_one()
        cad_name = (self.cad_name or "").strip()
        if not cad_name:
            raise UserError(_("Choose the CAD of the conversions."))
        formats = self.env["plm.convert.format"]
        made = formats
        for line in self.template_id.line_ids:
            mode = self._export_mode(line)
            found = formats.search(
                [
                    ("server_id", "=", self.server_id.id),
                    ("start_format", "=ilike", line.start_format),
                    ("end_format", "=ilike", line.end_format),
                    ("cad_name", "=ilike", cad_name),
                    ("cad_export_mode", "=", mode),
                ],
                limit=1,
            )
            if found:
                if not found.available:
                    found.available = True
                continue
            made |= formats.create(
                {
                    "server_id": self.server_id.id,
                    "start_format": line.start_format,
                    "end_format": line.end_format,
                    "cad_name": cad_name,
                    "cad_export_mode": mode,
                    "available": True,
                }
            )
        return made

    def action_add_and_close(self):
        self.action_add()
        return {"type": "ir.actions.act_window_close"}
