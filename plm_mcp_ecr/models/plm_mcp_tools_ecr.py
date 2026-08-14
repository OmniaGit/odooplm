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
"""Change requests and change orders, asked of the MCP server.

An engineering change here is a mail.activity that activity_validation extends:
plm_state carries where it sits in its own little workflow, is_eco separates a
change order from the request that asked for it, and the assigned user is who
has to act next. Closing one archives it rather than deleting it, so the history
stays readable — which is why the closed ones have to be asked for explicitly
instead of appearing by default.

"What do I have to validate" is answered without asking who is asking. Tools run
in the environment of the API key's user, so the person is already known, and a
tool that took a user name would let anyone read anyone else's queue by typing a
different name.
"""
import logging

from odoo import api, fields, models

from odoo.addons.plm_mcp.models.plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
# Everything that is not finished: what "open" means for a change.
OPEN_STATES = ("draft", "in_progress", "eco", "exception")


class PlmMcpToolsEcr(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    @mcp_tool(
        "plm_change_requests",
        """
        The engineering change requests and change orders that are open: what
        was asked, on which part, who has it, and where it stands.

        Use it for "what changes are open", "what is waiting", "which requests
        are on this part". A request (ECR) is the ask; a change order (ECO) is
        the work that follows it, and is_eco tells them apart.

        Closed changes are archived rather than deleted, and are left out unless
        include_closed is set — the history is there, but "what is open" is the
        question this answers, and mixing the two would inflate every count.

        plm_state is the change's own state: draft, in_progress, eco (promoted
        to a change order), exception (something blocked it), done, cancel.
        """,
        properties={
            "part": {
                "type": "string",
                "description": "Only changes on this engineering code, "
                               "e.g. 'BRG-HSG-001'.",
            },
            "state": {
                "type": "string",
                "enum": ["draft", "in_progress", "eco", "exception",
                         "done", "cancel"],
                "description": "Restrict to one state. Omit for the open ones.",
            },
            "kind": {
                "type": "string",
                "enum": ["request", "order"],
                "description": "'request' for ECRs, 'order' for ECOs. "
                               "Omit for both.",
            },
            "include_closed": {
                "type": "boolean",
                "description": "Include changes that were closed or cancelled. "
                               "Default false.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows, 1 to 200. Default 50.",
            },
        },
    )
    def plm_change_requests(self, part=None, state=None, kind=None,
                            include_closed=False, limit=DEFAULT_LIMIT):
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        domain = [("activity_type_id.change_activity_type", "!=", False)]

        if state:
            domain.append(("plm_state", "=", state))
        elif not include_closed:
            domain.append(("plm_state", "in", list(OPEN_STATES)))
        if kind == "order":
            domain.append(("is_eco", "=", True))
        elif kind == "request":
            domain.append(("is_eco", "=", False))
        if part:
            domain += self._part_domain(part)

        # A closed change is archived, so the default search would not see it
        # even when the caller asked for it by state.
        activities = self.env["mail.activity"].with_context(
            active_test=not include_closed and not state,
        ).search(domain, order="date_deadline asc, id desc", limit=limit)

        return {
            "open_only": not include_closed and not state,
            "count": len(activities),
            "changes": [self._change_row(activity) for activity in activities],
        }

    @mcp_tool(
        "plm_my_validations",
        """
        The engineering changes assigned to the person this connection belongs
        to, and still waiting on them.

        Use it for "what do I have to validate", "what is on my desk", "what am
        I holding up". It answers for whoever owns the API key in use — there is
        no user to pass, and that is deliberate: a queue is personal, and a tool
        that took a name would let anyone read somebody else's.

        Order the answer by deadline and say which ones are overdue: that is the
        part the person is actually asking about.
        """,
        properties={
            "include_closed": {
                "type": "boolean",
                "description": "Include what has already been handled. "
                               "Default false.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows, 1 to 200. Default 50.",
            },
        },
    )
    def plm_my_validations(self, include_closed=False, limit=DEFAULT_LIMIT):
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        domain = [
            ("activity_type_id.change_activity_type", "!=", False),
            ("user_id", "=", self.env.user.id),
        ]
        if not include_closed:
            domain.append(("plm_state", "in", list(OPEN_STATES)))

        activities = self.env["mail.activity"].with_context(
            active_test=not include_closed,
        ).search(domain, order="date_deadline asc, id desc", limit=limit)

        rows = [self._change_row(activity) for activity in activities]
        return {
            "user": self.env.user.name,
            "count": len(rows),
            "overdue": len([row for row in rows if row["is_overdue"]]),
            "changes": rows,
        }

    # -------------------------------------------------------------- helpers
    @api.model
    def _part_domain(self, code):
        """Changes recorded against a part, found by engineering code.

        Activities point at a record by model and id, so the code has to be
        resolved to products first: there is no join to follow from the activity
        side, and matching on the summary text would find whatever happens to
        mention the code.
        """
        products = self.env["product.product"].search(
            [("engineering_code", "=ilike", (code or "").strip())])
        if not products:
            return [("id", "=", False)]
        return [("res_model", "=", "product.product"),
                ("res_id", "in", products.ids)]

    @api.model
    def _change_row(self, activity):
        """One change, with the part it is about and who has it."""
        today = fields.Date.context_today(activity)
        deadline = activity.date_deadline
        return {
            "summary": activity.summary or activity.name,
            "kind": "order" if activity.is_eco else "request",
            "plm_state": activity.plm_state,
            "assigned_to": activity.user_id.name or None,
            "deadline": deadline,
            "is_overdue": bool(deadline and deadline < today
                               and activity.plm_state in OPEN_STATES),
            "created_on": activity.create_date,
            "is_closed": not activity.active,
            "part": self._change_part(activity),
        }

    @api.model
    def _change_part(self, activity):
        """The part a change is about, when it is about one."""
        if activity.res_model != "product.product" or not activity.res_id:
            return None
        product = self.env["product.product"].browse(activity.res_id).exists()
        if not product:
            return None
        return {
            "engineering_code": product.engineering_code,
            "engineering_revision": product.engineering_revision,
            "engineering_state": product.engineering_state,
            "name": product.name,
        }
