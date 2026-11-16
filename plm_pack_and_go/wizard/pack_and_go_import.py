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
"""Import a zip written by "Create zip archive checkout": replace each
matching document's content with the file from the zip and check it back
in. See pack_and_go_wizard.py's _write_export_manifest for the manifest
this reads (exported_data.json)."""
import hashlib
import io
import json
import logging
import zipfile

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MANIFEST_FILE = "exported_data.json"


class PackAndGoImport(models.TransientModel):
    _name = "pack.and.go.import"
    _description = "Import a Pack and Go zip"

    zip_file = fields.Binary(string="Zip file", required=True)
    zip_name = fields.Char(string="File name")
    state = fields.Selection(
        [("draft", "To import"), ("preview", "Preview"), ("done", "Imported")],
        default="draft",
    )
    result = fields.Text(string="Result", readonly=True)
    document_ids = fields.Many2many("ir.attachment", string="Documents", readonly=True)
    line_ids = fields.One2many(
        "pack.and.go.import.line", "import_id", string="Documents"
    )
    preview_2d_ids = fields.One2many(
        "pack.and.go.import.line",
        "import_id",
        string="2D",
        domain=[("doc_type", "=", "2d")],
    )
    preview_3d_ids = fields.One2many(
        "pack.and.go.import.line",
        "import_id",
        string="3D",
        domain=[("doc_type", "=", "3d")],
    )
    preview_other_ids = fields.One2many(
        "pack.and.go.import.line",
        "import_id",
        string="Other",
        domain=[("doc_type", "=", "other")],
    )

    def _read_zip(self):
        """The archive, {basename: path in the zip} and the parsed manifest."""
        self.ensure_one()
        try:
            archive = zipfile.ZipFile(io.BytesIO(self.zip_file.content))
        except zipfile.BadZipFile as ex:
            raise UserError(_("please upload only zip file this %s", ex)) from ex
        names = {
            name.rsplit("/", 1)[-1]: name
            for name in archive.namelist()
            if not name.endswith("/")
        }
        if MANIFEST_FILE not in names:
            raise UserError(
                _(
                    "The zip holds no %s: it was not built by \"Create zip "
                    "archive checkout\"",
                    MANIFEST_FILE,
                )
            )
        try:
            manifest = json.loads(archive.read(names[MANIFEST_FILE]).decode("utf-8"))
        except ValueError as ex:
            raise UserError(
                _("%(file)s is not valid json: %(error)s", file=MANIFEST_FILE, error=ex)
            ) from ex
        if not manifest.get("ir_attachment"):
            raise UserError(_("%s lists no document", MANIFEST_FILE))
        return archive, names, manifest

    def _find_document(self, entry):
        document = self.env["ir.attachment"].browse(entry["id"])
        if document.exists():
            return document
        return self.env["ir.attachment"].search(
            [
                ("engineering_code", "=", entry.get("engineering_code")),
                ("engineering_revision", "=", entry.get("engineering_revision")),
            ],
            limit=1,
        )

    def _preview_document(self, entry, archive, names):
        """A pack.and.go.import.line vals dict for entry: same lookups as
        _import_document, but read-only (no write, no check-in), plus the
        changed/unchanged split via a checksum comparison."""
        document = self._find_document(entry)
        if not document:
            return {
                "doc_type": "other",
                "status": "no_file",
                "message": _("%s: no longer in Odoo", entry.get("name")),
            }
        doc_type = (
            document.document_type
            if document.document_type in ("2d", "3d")
            else "other"
        )
        vals = {
            "document_id": document.id,
            "component_id": document.linkedcomponents[:1].product_tmpl_id.id,
            "doc_rev": document.engineering_revision,
            "doc_type": doc_type,
        }
        zip_path = names.get(document.name)
        if not zip_path:
            return dict(vals, status="no_file", message=_("No matching file in the zip"))
        if not document.isCheckedOutByMe():
            return dict(vals, status="not_checked_out")
        new_checksum = hashlib.sha1(archive.read(zip_path)).hexdigest()
        changed = new_checksum != document.checksum
        return dict(vals, status="changed" if changed else "unchanged")

    def action_load_preview(self):
        self.ensure_one()
        archive, names, manifest = self._read_zip()
        lines = [
            (0, 0, self._preview_document(entry, archive, names))
            for entry in manifest["ir_attachment"]
        ]
        self.write({"line_ids": [(5, 0, 0)] + lines, "state": "preview"})
        return {
            "type": "ir.actions.act_window",
            "name": _("Preview"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _import_document(self, entry, archive, names):
        """Replace document's content with the zip's file of the same name
        and check it in. Returns (document or False, log message): a
        document only comes back on full success, so one failure cannot be
        counted as imported."""
        document = self._find_document(entry)
        if not document:
            return False, _("%s: no longer in Odoo, left as it is", entry.get("name"))
        zip_path = names.get(document.name)
        if not zip_path:
            return False, _(
                "%s: no matching file in the zip, left as it is", document.name
            )
        if not document.isCheckedOutByMe():
            return False, _(
                "%s: not checked out by you, left as it is", document.name
            )
        try:
            with self.env.cr.savepoint():
                document.with_context(odooPLM=True).write(
                    {"raw": archive.read(zip_path)}
                )
                if document._check_in():
                    return document, _(
                        "%s: content replaced and checked in", document.name
                    )
                return False, _(
                    "%s: content replaced but could not be checked in",
                    document.name,
                )
        except UserError as ex:
            return False, _("%(name)s: %(error)s", name=document.name, error=ex)

    def action_import(self):
        self.ensure_one()
        archive, names, manifest = self._read_zip()
        log = []
        imported = self.env["ir.attachment"]
        for entry in manifest["ir_attachment"]:
            document, message = self._import_document(entry, archive, names)
            log.append(str(message))
            if document:
                imported |= document
        self.write(
            {
                "state": "done",
                "result": "\n".join(log),
                "document_ids": [(6, 0, imported.ids)],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported data"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported documents"),
            "res_model": "ir.attachment",
            "view_mode": "kanban,list,form",
            "views": [
                (self.env.ref("plm.document_kanban_view").id, "kanban"),
                (self.env.ref("plm.ir_attachment_list").id, "list"),
                (self.env.ref("plm.view_attachment_form_plm_hinerit").id, "form"),
            ],
            "domain": [("id", "in", self.document_ids.ids)],
            "context": {"odooPLM": True},
        }
