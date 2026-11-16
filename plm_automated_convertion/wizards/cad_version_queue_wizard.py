# -*- coding: utf-8 -*-
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.plm_cad_agent_stack import CAD_VERSION_OPERATION, CONVERT_OPERATION, OPEN_CAD_AGENT_STATES

RELEASED_STATE = "released"
DRAFT_STATE = "draft"


class PlmCadVersionQueueWizard(models.TransientModel):
    _name = "plm.cad.version.queue.wizard"
    _description = "Massive Update"

    def _default_selection_mode(self):
        if self.env.context.get("active_model") == "ir.attachment" and self.env.context.get("active_ids"):
            return "selection"
        return "not_checked_out"

    def _default_convert_format_ids(self):
        return self.env["plm.convert.format"].search(self._convert_format_domain(CAD_VERSION_OPERATION))

    def _default_document_ids(self):
        if self.env.context.get("active_model") == "ir.attachment":
            return [(6, 0, self.env.context.get("active_ids") or [])]
        return [(6, 0, [])]

    @api.model
    def _convert_format_domain(self, operation_type):
        if operation_type == CONVERT_OPERATION:
            return [
                ("cad_export_mode", "!=", False),
                ("server_id.cad_agent", "=", True),
                ("available", "=", True),
            ]
        return [("cad_version_update", "=", True), ("available", "=", True)]

    operation_type = fields.Selection(
        [
            (CAD_VERSION_OPERATION, "CAD version update"),
            (CONVERT_OPERATION, "Conversion of the files"),
        ],
        string="Operation",
        required=True,
        default=CAD_VERSION_OPERATION,
    )
    selection_mode = fields.Selection(
        [
            ("not_checked_out", "All documents not checked out"),
            ("not_draft", "All documents not in draft"),
            ("released", "Only released documents"),
            ("selection", "Selected documents"),
        ],
        string="Documents",
        required=True,
        default=_default_selection_mode,
    )
    convert_format_ids = fields.Many2many(
        "plm.convert.format",
        string="Conversions",
        default=_default_convert_format_ids,
        help="The conversions to queue: their start format chooses the files.",
    )
    document_ids = fields.Many2many("ir.attachment", string="Selected Documents", default=_default_document_ids)

    @api.onchange("operation_type")
    def _onchange_operation_type(self):
        self.convert_format_ids = self.env["plm.convert.format"].search(
            self._convert_format_domain(self.operation_type)
        )

    def _format_by_extension(self):
        """{".ipt": plm.convert.format(...), ...}; a CAD version update has
        one conversion per extension, a conversion of the files can have
        more (STEP and DXF of a part)."""
        allowed = self.env["plm.convert.format"].search(self._convert_format_domain(self.operation_type))
        out = {}
        for convert_format in self.convert_format_ids:
            if convert_format not in allowed:
                raise UserError(_("The conversion %s does not belong to the operation chosen.", convert_format.name))
            extension = (convert_format.start_format or "").strip().lower()
            if not extension:
                continue
            formats = out.setdefault(extension, self.env["plm.convert.format"])
            if self.operation_type == CAD_VERSION_OPERATION and formats and formats != convert_format:
                raise UserError(_("Two conversions start from the format %s: choose only one.", extension))
            out[extension] = formats | convert_format
        return out

    def _target_versions(self, formats):
        """{conversion id: the target version of its CAD} for a CAD version
        update: the version comes from the CAD (PLM dictionaries, CAD
        Versions), the same for every file format of that CAD."""
        targets = {}
        cads = self.env["plm.cad"].sudo()
        all_formats = self.env["plm.convert.format"].browse()
        for extension_formats in formats.values():
            all_formats |= extension_formats
        for convert_format in all_formats:
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

    def _document_domain(self, extensions):
        domain = [("is_plm", "=", True)]
        name_domain = []
        for extension in extensions:
            if name_domain:
                name_domain.insert(0, "|")
            name_domain.append(("name", "=ilike", "%" + extension))
        domain += name_domain
        if self.selection_mode == "selection":
            domain.append(("id", "in", self.document_ids.ids))
        elif self.selection_mode == "not_checked_out":
            checked_out_ids = self.env["plm.checkout"].sudo().search([]).mapped("documentid").ids
            domain.append(("id", "not in", checked_out_ids))
        elif self.selection_mode == "not_draft":
            domain.append(("engineering_state", "!=", DRAFT_STATE))
        elif self.selection_mode == "released":
            domain.append(("engineering_state", "=", RELEASED_STATE))
        return domain

    def action_queue(self):
        self.ensure_one()
        formats = self._format_by_extension()
        if not formats:
            raise UserError(_("Choose at least one conversion."))
        targets = self._target_versions(formats) if self.operation_type == CAD_VERSION_OPERATION else {}
        stack = self.env["plm.convert.stack"].sudo()
        documents = self.env["ir.attachment"].sudo().search(self._document_domain(list(formats)), order="id")
        # (document, conversion) already waiting or held by an agent
        queued = {
            (row.start_document_id.id, row.convrsion_rule.id)
            for row in stack.search(
                [
                    ("operation_type", "=", self.operation_type),
                    ("cad_agent_state", "in", OPEN_CAD_AGENT_STATES),
                    ("start_document_id", "in", documents.ids),
                ]
            )
        }
        queued_documents = {document_id for document_id, _rule_id in queued}
        values = []
        for document in documents:
            for convert_format in formats.get(os.path.splitext(document.name or "")[1].lower(), []):
                if self.operation_type == CAD_VERSION_OPERATION:
                    if document.id in queued_documents or document.cad_version == targets[convert_format.id]:
                        continue
                elif (document.id, convert_format.id) in queued:
                    continue
                row_values = {
                    "operation_type": self.operation_type,
                    "start_document_id": document.id,
                    "convrsion_rule": convert_format.id,
                    "cad_agent_state": "to_do",
                    "conversion_done": False,
                }
                if self.operation_type == CAD_VERSION_OPERATION:
                    row_values["cad_version_target"] = targets[convert_format.id]
                values.append(row_values)
        rows = stack.create(values) if values else stack
        return {
            "name": _("CAD Workstation Queue"),
            "type": "ir.actions.act_window",
            "res_model": "plm.convert.stack",
            "view_mode": "list,form",
            "domain": [("id", "in", rows.ids)],
            "context": {"create": False},
        }
