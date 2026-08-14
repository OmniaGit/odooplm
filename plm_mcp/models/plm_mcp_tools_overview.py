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
"""The shape of the whole environment, in one call.

Every other tool answers about one part, one code, one pair of revisions. The
questions that start "how many" or "what is in here" had no tool at all, and a
model without one does something worse than refusing: it reaches for the
nearest search, gets nothing, and reports that the data does not exist.

This is also what a model should read before answering anything else in an
unfamiliar database. Knowing there are four bills of material and eleven parts
in draft is what lets it say "there are four, but I cannot open them" instead of
implying there are none — the difference between a bounded answer and a wrong
one.

Everything is counted through the ORM rather than in SQL, so the numbers are the
ones the key's user is allowed to see. A user who cannot read obsoleted parts
gets a total that excludes them, which is the honest figure for that person.
"""
import logging

from odoo import api, models

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)


class PlmMcpToolsOverview(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    @mcp_tool(
        "plm_overview",
        """
        A snapshot of the whole PLM environment: how many engineering parts
        there are and in which lifecycle states, how many carry more than one
        revision, how many bills of material of each type, how many engineering
        documents of each type, and how many documents are currently checked out
        for editing.

        Answers any "how many" question about the database, and is worth calling
        first when you do not know what this environment contains: the totals
        tell you whether something exists at all, so you can say what you cannot
        reach rather than implying it is absent.
        """,
    )
    def plm_overview(self):
        return {
            "parts": self._overview_parts(),
            "bills_of_material": self._overview_boms(),
            "documents": self._overview_documents(),
            # sudo, as everywhere else this module reads a checkout: the lock
            # table is not readable by an ordinary engineering user, and without
            # it the whole overview would be refused to exactly the people it is
            # written for. What is exposed is a count of locks — who holds which
            # document is still answered by plm_in_progress, under their rights.
            "checked_out_documents": self.env["plm.checkout"].sudo().search_count([]),
        }

    # -------------------------------------------------------------- sections
    @api.model
    def _overview_parts(self):
        """Parts by lifecycle state, plus how much revision history exists.

        The three figures answer different questions: how much there is, how
        many distinct designs that represents, and how many of those designs
        have been revised at least once — which is the one that says whether
        this environment is actually being used as a PLM.
        """
        domain = [("engineering_code", "!=", False)]
        by_state = self.env["product.product"]._read_group(
            domain, groupby=["engineering_state"], aggregates=["__count"])
        states = {state or "unset": count for state, count in by_state}

        # One row per code: the same grouping gives both the number of distinct
        # designs and how many of them carry a history, without a second query.
        by_code = self.env["product.product"]._read_group(
            domain, groupby=["engineering_code"], aggregates=["__count"])
        codes = [count for _code, count in by_code]

        return {
            "total": sum(codes),
            "distinct_codes": len(codes),
            "codes_with_more_than_one_revision": len([c for c in codes if c > 1]),
            "by_state": states,
        }

    @api.model
    def _overview_boms(self):
        """Bills of material by type, with how many lines each type holds."""
        by_type = self.env["mrp.bom"]._read_group(
            [], groupby=["type"], aggregates=["__count"])
        lines_by_type = self.env["mrp.bom.line"]._read_group(
            [], groupby=["type"], aggregates=["__count"])
        lines = {bom_type or "unset": count for bom_type, count in lines_by_type}

        return {
            "total": sum(count for _t, count in by_type),
            "by_type": [{
                "type": bom_type or "unset",
                "bills": count,
                "lines": lines.get(bom_type or "unset", 0),
            } for bom_type, count in by_type],
        }

    @api.model
    def _overview_documents(self):
        """Engineering documents by type and by lifecycle state.

        is_plm is what separates a drawing from an ordinary attachment: without
        it the count would include every logo, mail attachment and report ever
        stored in the database, and be useless as an answer.
        """
        domain = [("is_plm", "=", True)]
        by_type = self.env["ir.attachment"]._read_group(
            domain, groupby=["document_type"], aggregates=["__count"])
        by_state = self.env["ir.attachment"]._read_group(
            domain, groupby=["engineering_state"], aggregates=["__count"])

        return {
            "total": sum(count for _t, count in by_type),
            "by_type": {doc_type or "unset": count for doc_type, count in by_type},
            "by_state": {state or "unset": count for state, count in by_state},
        }
