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
"""Where a part is used, revision by revision.

The revision is not a detail here, it is the answer. A part is identified by its
engineering code *and* its revision, so each revision is used in its own set of
assemblies: the released one is in production, the draft that replaces it is
usually in nothing yet. Reporting a single list against the code would blur the
two and produce the two worst answers this tool can give — "it is used nowhere"
about a part running in production, or "it is used in these assemblies" about a
draft that has never been built.

So the answer is grouped by revision, always, even when only one exists. What an
engineer is really asking is what would be affected by a change, and that
question only has a meaning once you know which revision you are changing.

Both bill of material types are searched. A part that appears only in a spare
parts bill is in a different situation from one in the manufacturing bill, and
each row says which one it came from.
"""
import logging

from odoo import api, models
from odoo.exceptions import UserError

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

MAX_DEPTH = 10


class PlmMcpToolsWhereUsed(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    @mcp_tool(
        "plm_where_used",
        """
        The assemblies that use a part, walking up every level, grouped by the
        revision of the part.

        This is the impact question: what would be affected by changing,
        revising or obsoleting this part. Call it before advising any change.

        Read the grouping carefully. Each revision has its own list, because a
        revision is a distinct part: revision 0 released and running in
        production can be used in several assemblies while revision 1, still in
        draft, is used in none — that is normal and means the new revision has
        not been built into anything yet. An empty list for one revision never
        means the code is unused; check the other revisions before saying so.

        Rows from the spare parts bill are marked as such: a part used only
        there is not in the manufacturing structure.
        """,
        properties={
            "code": {
                "type": "string",
                "description": "Exact engineering code, e.g. 'BRG-HSG-001'.",
            },
            "revision": {
                "type": "integer",
                "description": "Restrict to one revision. Omit to get them all, "
                               "which is usually what you want.",
            },
            "bom_type": {
                "type": "string",
                "description": "'normal' or 'spbom' to restrict to one kind of "
                               "bill. Omit for both.",
            },
            "depth": {
                "type": "integer",
                "description": "How many levels to walk up. Default 10, enough "
                               "for the whole structure in practice.",
            },
        },
        required=["code"],
    )
    def plm_where_used(self, code=None, revision=None, bom_type=None,
                       depth=MAX_DEPTH):
        code = (code or "").strip()
        depth = max(1, min(int(depth or MAX_DEPTH), MAX_DEPTH))
        bom_type = (bom_type or "").strip() or None

        products = self.env["product.product"].search(
            [("engineering_code", "=ilike", code)],
            order="engineering_revision desc")
        if revision is not None:
            products = products.filtered(
                lambda p: p.engineering_revision == int(revision))
        if not products:
            raise UserError(self._no_part(code, revision))

        revisions = []
        for product in products:
            parents = self._where_used_tree(product, bom_type, depth)
            revisions.append({
                "engineering_revision": product.engineering_revision,
                "engineering_state": product.engineering_state,
                # The count is of assemblies reached at any level, so a caller
                # can see at a glance which revision is the one in use.
                "used_in_count": self._count_nodes(parents),
                "used_in": parents,
            })

        return {
            "engineering_code": products[0].engineering_code,
            "bom_type": bom_type or "all",
            "revisions": revisions,
        }

    # ------------------------------------------------------------- the walk
    @api.model
    def _where_used_tree(self, product, bom_type, depth, seen=None):
        """The assemblies using this exact part, and what uses those in turn."""
        domain = [("product_id", "=", product.id)]
        if bom_type:
            domain.append(("type", "=", bom_type))
        lines = self.env["mrp.bom.line"].search(domain)

        # A part can appear on several rows of the same bill — different
        # positions, same parent. Merged into one entry with the quantities
        # added, because "used twice in this assembly" is one fact, not two.
        merged = {}
        for line in lines:
            parent = line.bom_id.product_tmpl_id.product_variant_id
            if not parent:
                continue
            key = (parent.id, line.bom_id.type)
            entry = merged.get(key)
            if entry is None:
                entry = self._part_summary(parent)
                entry.update({
                    "bom_type": line.bom_id.type,
                    "quantity": 0.0,
                    "positions": [],
                    "_parent": parent,
                })
                merged[key] = entry
            entry["quantity"] += line.product_qty
            if line.itemnum:
                entry["positions"].append(line.itemnum)

        seen = set(seen or ())
        seen.add(product.id)

        parents = []
        for entry in merged.values():
            parent = entry.pop("_parent")
            entry["positions"] = sorted(set(entry["positions"])) or None
            if depth > 1 and parent.id not in seen:
                entry["used_in"] = self._where_used_tree(
                    parent, bom_type, depth - 1, seen)
            elif parent.id in seen:
                # Only happens on data where an assembly contains itself through
                # a chain; stopping quietly would hide that the data is broken.
                entry["note"] = "cycle stopped — this assembly appears above"
            parents.append(entry)

        parents.sort(key=lambda row: (row["engineering_code"] or "",
                                      row["engineering_revision"] or 0))
        return parents

    @api.model
    def _count_nodes(self, nodes):
        """Assemblies reached at any level, counted once each."""
        total = 0
        for node in nodes:
            total += 1 + self._count_nodes(node.get("used_in") or [])
        return total
