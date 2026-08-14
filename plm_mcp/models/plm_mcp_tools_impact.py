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
"""What changing a part would touch.

The question is asked before every modification and answered, in most companies,
by someone who remembers. It has more than one dimension, and the danger is not
getting one wrong — it is forgetting one exists:

the assemblies that use the part, and how many of them are released, which is
the difference between editing a draft and changing something being built;
whether the part is in a spare parts list, because then the manual and the
ballooned sheets move too, and that is remembered last;
whether a revision is already open, meaning somebody else started this change;
whether a drawing exists at all, because a missing sheet is something to create
rather than update;
whether a document is checked out, meaning a file is open in someone's CAD right
now.

Each of those is available on its own from another tool. They are gathered here
because an impact assessment that quietly omits one is worse than none: it reads
as complete, and the reader stops looking.

Nothing here is scored or ranked. The facts are laid out with the counts that
make them comparable, and the judgement — is this cheap or expensive, safe or
not — stays with whoever knows what the change actually is.
"""
import logging

from odoo import api, models
from odoo.exceptions import UserError

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

MAX_DEPTH = 10
OPEN_STATES = ("draft", "confirmed", "undermodify")


class PlmMcpToolsImpact(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    @mcp_tool(
        "plm_change_impact",
        """
        What modifying a part would affect: the assemblies that use it, whether
        the spare parts list is involved, what documentation exists, and whether
        somebody is already working on it.

        Call this before advising or planning any change to a part — it is the
        question "what breaks if I touch this", answered in one place so that no
        dimension of it is forgotten.

        How to read what comes back:

        assemblies_released is the production risk. Changing a part used only in
        drafts is cheap; changing one inside released assemblies means a formal
        revision and everything that follows from it.

        affects_spare_list means the change reaches the spare parts manual and
        its ballooned sheets, not only manufacturing. This is the dimension
        people forget.

        revision_in_progress means a newer revision of this part already exists
        and is not released — somebody started this change before you. Say so
        plainly; two people revising the same part is the expensive mistake this
        tool exists to prevent.

        has_drawing false means there is nothing to update, only something to
        create. checked_out_documents means a file is open in someone's CAD
        session right now, and editing it elsewhere will be lost.

        Report the counts and the flags, and let the person weigh them. Do not
        pronounce a change safe: whether it is depends on what the change is,
        which is not in the database.
        """,
        properties={
            "code": {
                "type": "string",
                "description": "Exact engineering code of the part, "
                               "e.g. 'CLP-020-001'.",
            },
            "revision": {
                "type": "integer",
                "description": "Assess this revision only. Omit to assess every "
                               "revision of the code, which is usually right.",
            },
            "depth": {
                "type": "integer",
                "description": "How many levels up to walk. Default 10.",
            },
        },
        required=["code"],
    )
    def plm_change_impact(self, code=None, revision=None, depth=MAX_DEPTH):
        code = (code or "").strip()
        depth = max(1, min(int(depth or MAX_DEPTH), MAX_DEPTH))

        products = self.env["product.product"].search(
            [("engineering_code", "=ilike", code)],
            order="engineering_revision desc")
        if revision is not None:
            products = products.filtered(
                lambda p: p.engineering_revision == int(revision))
        if not products:
            raise UserError(self._no_part(code, revision))

        revisions = [self._impact_for(product, depth) for product in products]
        newest = products[0]

        # A revision that exists and is not released is somebody's work in
        # progress. Reported as its own fact rather than left to be inferred
        # from a list of states, because it is the one collision that costs
        # real money.
        in_progress = next(
            ({"engineering_revision": p.engineering_revision,
              "engineering_state": p.engineering_state}
             for p in products if p.engineering_state in OPEN_STATES), None)

        documents = self._document_state(newest)
        return {
            "part": self._part_summary(newest),
            "revisions": self._revision_history(newest.engineering_code),
            "revision_in_progress": in_progress,
            "documents": documents,
            "impact": revisions,
            "flags": {
                "affects_released_assemblies": any(
                    rev["assemblies_released"] for rev in revisions),
                "affects_spare_list": any(
                    "spbom" in rev["bom_types"] for rev in revisions),
                "revision_in_progress": bool(in_progress),
                "has_drawing": documents["has_drawing"],
                "documents_checked_out": bool(documents["checked_out"]),
            },
        }

    # -------------------------------------------------------------- gather
    @api.model
    def _impact_for(self, product, depth):
        """The assemblies one revision of the part sits in, and what they are."""
        assemblies = self._where_used_tree(product, None, depth)
        flat = self._flatten(assemblies)
        return {
            "engineering_revision": product.engineering_revision,
            "engineering_state": product.engineering_state,
            "assemblies_count": len(flat),
            # Released parents are the ones already built or being built; the
            # count is what separates a paper change from a production one.
            "assemblies_released": len(
                [row for row in flat if row["engineering_state"] == "released"]),
            "bom_types": sorted({row["bom_type"] for row in flat}),
            "assemblies": assemblies,
        }

    @api.model
    def _flatten(self, nodes, collected=None):
        """Every assembly reached at any level, each counted once."""
        collected = [] if collected is None else collected
        for node in nodes:
            collected.append(node)
            self._flatten(node.get("used_in") or [], collected)
        return collected

    @api.model
    def _document_state(self, product):
        """What documentation exists for the part, and who is holding it."""
        documents = product.linkeddocuments
        printouts = self._printout_ids(documents)
        checked_out = self._checked_out_ids(documents)
        drawings = [d for d in documents
                    if d.id in self._lytree_drawings(documents)
                    or d.document_type == "2d"]
        models = [d for d in documents
                  if d.id in self._lytree_models(documents)
                  or d.document_type == "3d"]
        return {
            "has_drawing": bool(drawings),
            "has_model": bool(models),
            "has_printout": any(d.id in printouts for d in drawings),
            "checked_out": [d.name for d in documents if d.id in checked_out],
            "count": len(documents),
        }
