# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
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
"""The customer's frames and title blocks, for the CAD client (2026-11-26).

The groups name them (res.groups plm_frame_document_ids and
plm_titleblock_document_ids); every client downloads those of its user's
groups, so a frame or a title block changed on the server reaches every
client. A document stands for its code: the client gets the highest revision
of that code, whatever revision the group links.
"""
import base64
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# What the client is told each document is, and the group field naming them.
SHEET_TEMPLATE_FIELDS = (
    ("frame", "plm_frame_document_ids"),
    ("titleblock", "plm_titleblock_document_ids"),
)


class PlmClient(models.TransientModel):
    _inherit = "plm.client"

    @api.model
    def _sheet_template_documents(self):
        """[(kind, attachment)] for the groups of this user, implied groups
        included, each code at its highest revision, each document once per
        kind.

        Read as superuser: a template is offered to whoever is in the group,
        which is the administrator's choice, and the members need not be able
        to read the group or every revision of the document."""
        groups = self.env.user.sudo().all_group_ids
        attachment = self.env["ir.attachment"].sudo()
        out = []
        for kind, field_name in SHEET_TEMPLATE_FIELDS:
            seen = set()
            for linked in groups.mapped(field_name):
                latest = linked
                if linked.engineering_code:
                    latest = attachment.search(
                        [("engineering_code", "=", linked.engineering_code)],
                        order="engineering_revision DESC, id DESC",
                        limit=1,
                    ) or linked
                if latest.id in seen:
                    continue
                seen.add(latest.id)
                out.append((kind, latest))
        return out

    @api.model
    def get_sheet_templates(self):
        """The frames and title blocks this user's client offers: a list of
        {id, kind ('frame' or 'titleblock'), file_name, engineering_code,
        engineering_revision, write_date}, sorted by kind and file name. The
        client downloads the files whose revision or date it does not have
        (get_sheet_template_files) and drops those no longer listed."""
        out = []
        for kind, document in self._sheet_template_documents():
            out.append({
                "id": document.id,
                "kind": kind,
                "file_name": document.name or "",
                "engineering_code": document.engineering_code or "",
                "engineering_revision": document.engineering_revision,
                "write_date": str(document.write_date or ""),
            })
        out.sort(key=lambda row: (row["kind"], row["file_name"].lower()))
        return out

    @api.model
    def get_sheet_template_files(self, attachment_ids):
        """{str(id): base64 content} of the templates asked for. Only the ones
        get_sheet_templates lists for this user are given: an id it does not
        list is left out and logged."""
        offered = {document.id: document for _kind, document in self._sheet_template_documents()}
        out = {}
        for attachment_id in attachment_ids or []:
            document = offered.get(attachment_id)
            if document is None:
                _logger.warning(
                    "get_sheet_template_files: %r is not a template of user %s",
                    attachment_id, self.env.user.login)
                continue
            # Odoo 20 has no datas: raw is the file itself
            out[str(attachment_id)] = base64.b64encode(bytes(document.raw or b"")).decode()
        return out
