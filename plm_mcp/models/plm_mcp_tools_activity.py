# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
"""Who is working on what, and what has just been released.

Both questions are about the workflow rather than the structure, and both are
asked about people as much as about parts: what is open right now and in whose
hands, what went out last week and who signed it off. The suite records all of
it — every state change stamps a user and a date — so the answers are facts, not
reconstructions.

Two tools rather than one with a switch. The questions are asked in different
situations, by different people, and what routes a request to the right tool is
the description: one that had to cover both would speak in generalities about
"workflow activity", which is where a model starts guessing.

A note on who. The workflow user is whoever last moved the record through the
lifecycle; the checkout user is whoever has the file open in a CAD session right
now. They are different facts and often different people — the first is who
decided, the second is who is typing — so both are reported and neither is
presented as "the owner".
"""
import logging
from datetime import timedelta

from odoo import api, fields, models

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
OPEN_STATES = ("draft", "confirmed", "undermodify")


class PlmMcpToolsActivity(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    # ------------------------------------------------------------- in flight
    @mcp_tool(
        "plm_in_progress",
        """
        What is being worked on right now, and by whom: documents and parts that
        are not released — under modification, confirmed or still in draft —
        together with who moved them there and who has a file checked out.

        Use it for "what is open", "what is under modification", "who is working
        on what", "who has this drawing". Answers about the present, not about
        history.

        Two different people can appear on one row. workflow_user is who last
        moved the record through the lifecycle; checked_out_by is who has the
        file open in a CAD session at this moment and would lose work if someone
        else edited it. Report both, and do not merge them into "the owner".
        """,
        properties={
            "target": {
                "type": "string",
                "enum": ["documents", "parts", "both"],
                "description": "What to look at. Default 'both'.",
            },
            "state": {
                "type": "string",
                "enum": ["draft", "confirmed", "undermodify"],
                "description": "Restrict to one state. Omit for all open ones.",
            },
            "user": {
                "type": "string",
                "description": "Only what this person moved or has checked out. "
                               "Matched on the name, e.g. 'Rossi'.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows, 1 to 200. Default 50.",
            },
        },
    )
    def plm_in_progress(self, target="both", state=None, user=None,
                        limit=DEFAULT_LIMIT):
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        states = [state] if state else list(OPEN_STATES)
        domain = [("engineering_state", "in", states),
                  ("engineering_code", "!=", False)]
        if user:
            domain.append(("engineering_workflow_user.name", "ilike", user.strip()))

        result = {"states": states, "user": user or None}
        if target in ("documents", "both"):
            documents = self.env["ir.attachment"].search(
                domain + [("is_plm", "=", True)],
                order="engineering_workflow_date desc, id desc", limit=limit)
            checked_out = self._checked_out_ids(documents)
            holders = self._checkout_holders(documents)
            result["documents"] = [{
                **self._workflow_row(document),
                "document_type": document.document_type,
                "is_checked_out": document.id in checked_out,
                "checked_out_by": holders.get(document.id),
            } for document in documents]
        if target in ("parts", "both"):
            parts = self.env["product.product"].search(
                domain, order="engineering_workflow_date desc, id desc",
                limit=limit)
            result["parts"] = [self._workflow_row(part) for part in parts]
        return result

    # ------------------------------------------------------------- released
    @mcp_tool(
        "plm_recent_releases",
        """
        What has been released in a period, and by whom: documents and parts
        whose release date falls in the window, newest first.

        Use it for "what went out last week", "what was released this month",
        "what did we approve since Monday". Answers about history, not about
        what is open now.

        The release date is stamped when the record reaches the released state,
        so this is what was actually signed off, not what was drawn or edited in
        the period. A part revised three weeks ago and released yesterday
        appears under yesterday.
        """,
        properties={
            "days": {
                "type": "integer",
                "description": "How far back to look, in days. Default 7.",
            },
            "target": {
                "type": "string",
                "enum": ["documents", "parts", "both"],
                "description": "What to look at. Default 'both'.",
            },
            "user": {
                "type": "string",
                "description": "Only what this person released. Matched on the "
                               "name, e.g. 'Rossi'.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows, 1 to 200. Default 50.",
            },
        },
    )
    def plm_recent_releases(self, days=7, target="both", user=None,
                            limit=DEFAULT_LIMIT):
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        days = max(1, int(days or 7))
        since = fields.Datetime.now() - timedelta(days=days)

        domain = [("engineering_release_date", ">=", since),
                  ("engineering_code", "!=", False)]
        if user:
            domain.append(("engineering_release_user.name", "ilike", user.strip()))

        result = {"since": since, "days": days, "user": user or None}
        if target in ("documents", "both"):
            documents = self.env["ir.attachment"].search(
                domain + [("is_plm", "=", True)],
                order="engineering_release_date desc", limit=limit)
            result["documents"] = [{
                **self._workflow_row(document),
                "document_type": document.document_type,
            } for document in documents]
        if target in ("parts", "both"):
            parts = self.env["product.product"].search(
                domain, order="engineering_release_date desc", limit=limit)
            result["parts"] = [self._workflow_row(part) for part in parts]
        return result

    # -------------------------------------------------------------- helpers
    @api.model
    def _workflow_row(self, record):
        """A record with the people and the dates its state carries."""
        return {
            "engineering_code": record.engineering_code,
            "engineering_revision": record.engineering_revision,
            "engineering_state": record.engineering_state,
            "name": record.name,
            "workflow_user": record.engineering_workflow_user.name or None,
            "workflow_date": record.engineering_workflow_date,
            "release_user": record.engineering_release_user.name or None,
            "release_date": record.engineering_release_date,
            "revision_user": record.engineering_revision_user.name or None,
            "revision_date": record.engineering_revision_date,
        }

    @api.model
    def _checkout_holders(self, documents):
        """Who is holding each document open, by document id."""
        if not documents:
            return {}
        checkouts = self.env["plm.checkout"].sudo().search(
            [("documentid", "in", documents.ids)])
        return {checkout.documentid.id: checkout.userid.name
                for checkout in checkouts}
