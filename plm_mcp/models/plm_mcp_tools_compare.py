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
"""Comparing two bills of material.

The rules come from how the suite defines a component, and they are not the
obvious ones.

A line is identified by engineering code *and* revision: BRG-HSG-001 at revision
0 and at revision 1 are different components, not the same one changed. Taken
alone that rule would report every revised child as one line on each side,
which is technically right and useless to read — so a code present on both
sides at different revisions gets its own category, revision_changed, and
the walk descends into it. Descending is the whole point: a pair that matches on
code *and* revision has an identical structure underneath, so the only place
where anything can differ is exactly the pair the strict rule would have
refused to follow.

The two sides are independent — each has its own code, revision and bill type —
because the three questions people actually ask are "what changed between these
two revisions", "how does the manufacturing bill differ from the spare parts
one", and "how do these two similar products differ". Only the first has one
code, and a signature built for it would have made the other two impossible.

Each side keeps its own bill type all the way down: normal on the left stays
normal, spare on the right stays spare. Swapping type mid-walk would produce a
tree nobody could interpret.

The walk itself lives in the module plm_compare_bom (plm.compare.bom.tree),
which the comparison screen of the suite uses too. This module does not depend
on it: without it the tool says which module to install.
"""
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

MAX_DEPTH = 10


class PlmMcpToolsCompare(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    @mcp_tool(
        "plm_compare_bom",
        """
        Compare two bills of material, level by level, and report what differs.

        Three questions this answers, all with the same call: what changed
        between two revisions of a product (same code, two revisions), how the
        manufacturing bill differs from the spare parts one (same code, two bill
        types), and how two similar products differ (two codes).

        Every line comes back in one of five states:
        only_left — present on the left side and not on the right;
        only_right — present on the right and not on the left;
        qty_changed — same component, different quantity;
        revision_changed — same code at a different revision, which is the one
        to read first because it means a child part was revised;
        unchanged.

        The two one-sided states say where a line is, not what happened to it.
        Comparing two revisions of the same product, only_left does mean the
        component was taken out — but comparing a manufacturing bill against a
        spare parts one, or two similar products, nothing was added or removed
        at all: the two bills simply differ. Describe what the state says, and
        let the comparison you were asked for supply the rest.

        The answer is one tree: every component carries its own comparison
        underneath, the way a bill of material nests. A component tells you what
        lies below it through has_components:

        has_components false — a part, there is nothing under it to compare;
        has_components true with a components list — a subassembly whose
        contents differ, and the list is the difference;
        has_components true with no components list — a subassembly that was
        compared and came out identical.

        So an unchanged line is never ambiguous: you can always tell "there was
        nothing to look at" from "I looked and it was the same".

        A component without an engineering code (a commercial part) is matched
        by product: its engineering_code is false and its default_code names it.
        """,
        properties={
            "code_a": {
                "type": "string",
                "description": "Engineering code of the left side.",
            },
            "revision_a": {
                "type": "integer",
                "description": "Revision of the left side. Omit for the newest.",
            },
            "bom_type_a": {
                "type": "string",
                "description": "Bill type of the left side: 'normal' or 'spbom'. "
                               "Default 'normal'.",
            },
            "code_b": {
                "type": "string",
                "description": "Engineering code of the right side. Use the same "
                               "code as the left to compare two revisions.",
            },
            "revision_b": {
                "type": "integer",
                "description": "Revision of the right side. Omit for the newest.",
            },
            "bom_type_b": {
                "type": "string",
                "description": "Bill type of the right side. Default 'normal'.",
            },
            "max_depth": {
                "type": "integer",
                "description": "How many levels to compare. Default 10.",
            },
        },
        required=["code_a", "code_b"],
    )
    def plm_compare_bom(self, code_a=None, revision_a=None, bom_type_a="normal",
                        code_b=None, revision_b=None, bom_type_b="normal",
                        max_depth=MAX_DEPTH):
        # plm_compare_bom holds the comparison; this module does not depend
        # on it, so the tool says what is missing instead of failing.
        if "plm.compare.bom.tree" not in self.env:
            raise UserError(_(
                "Comparing bills of material needs the module PLM Compare Bom "
                "(plm_compare_bom): install it to use this tool."))
        left = self._find_part(code_a, revision_a)
        if not left:
            raise UserError(self._no_part(code_a, revision_a))
        right = self._find_part(code_b, revision_b)
        if not right:
            raise UserError(self._no_part(code_b, revision_b))

        bom_type_a = (bom_type_a or "normal").strip()
        bom_type_b = (bom_type_b or "normal").strip()
        depth = max(1, min(int(max_depth or MAX_DEPTH), MAX_DEPTH))

        node = self._without_ids(self.env["plm.compare.bom.tree"].compare_products(
            left, bom_type_a, right, bom_type_b, depth))
        # What was actually compared, echoed back: with three optional arguments
        # resolving to defaults, a caller that reads only the differences would
        # otherwise not know which revisions produced them.
        node["compared"] = {
            "left": self._side(left, bom_type_a),
            "right": self._side(right, bom_type_b),
        }
        return node

    # -------------------------------------------------------------- helpers
    @api.model
    def _side(self, product, bom_type):
        return {
            "engineering_code": product.engineering_code,
            "engineering_revision": product.engineering_revision,
            "engineering_state": product.engineering_state,
            "bom_type": bom_type,
        }

    @api.model
    def _bom_of(self, product, bom_type):
        return self.env["mrp.bom"].search([
            ("product_tmpl_id", "=", product.product_tmpl_id.id),
            ("type", "=", bom_type),
        ], limit=1)

    @api.model
    def _without_ids(self, node):
        """Record ids are for the comparison screen; they mean nothing to an
        agent."""
        clean = {key: value for key, value in node.items()
                 if not key.endswith(("_id", "_ids"))}
        if "components" in node:
            clean["components"] = [self._without_ids(row)
                                   for row in node["components"]]
        return clean
