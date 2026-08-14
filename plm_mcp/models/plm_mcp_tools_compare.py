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
"""
import logging

from odoo import api, models
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
        left = self._find_part(code_a, revision_a)
        if not left:
            raise UserError(self._no_part(code_a, revision_a))
        right = self._find_part(code_b, revision_b)
        if not right:
            raise UserError(self._no_part(code_b, revision_b))

        bom_type_a = (bom_type_a or "normal").strip()
        bom_type_b = (bom_type_b or "normal").strip()
        depth = max(1, min(int(max_depth or MAX_DEPTH), MAX_DEPTH))

        node = self._compare_node(left, bom_type_a, right, bom_type_b, depth)
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
    def _lines_by_code(self, bom):
        """Bill lines as {code: [entry]}, quantities of identical rows summed.

        The same component listed twice in one bill is one fact — two positions
        of the same part — so the quantities are added before anything is
        compared. Left as separate rows they would show up as a spurious
        difference whenever the other side happened to list it once.
        """
        by_code = {}
        for line in bom.bom_line_ids:
            component = line.product_id
            code = component.engineering_code
            if not code:
                continue
            entries = by_code.setdefault(code, {})
            entry = entries.get(component.engineering_revision)
            if entry is None:
                entry = {
                    "engineering_revision": component.engineering_revision,
                    "engineering_state": component.engineering_state,
                    "name": component.name,
                    "quantity": 0.0,
                    "itemnum": line.itemnum or None,
                    "product": component,
                }
                entries[component.engineering_revision] = entry
            entry["quantity"] += line.product_qty
            if line.itemnum and (entry["itemnum"] is None
                                 or line.itemnum < entry["itemnum"]):
                entry["itemnum"] = line.itemnum
        return by_code

    # ------------------------------------------------------------ the walk
    @api.model
    def _compare_node(self, left, type_left, right, type_right, depth, seen=None):
        """Compare one pair, and nest each component's own comparison under it.

        One shape all the way down: a component and the difference inside it are
        the same object, because a bill of material is a tree and splitting it
        into a list of rows plus a parallel list of subtrees made the same
        component appear twice.
        """
        bom_left = self._bom_of(left, type_left)
        bom_right = self._bom_of(right, type_right)

        if not bom_left and not bom_right:
            return {"note": "Neither side has a bill of material of this type.",
                    "components": []}
        if not bom_left or not bom_right:
            # One side only. Listing the other side's rows as wholesale
            # additions would read as a change; it is a missing bill, and saying
            # so is the useful part.
            side = "right" if bom_right else "left"
            missing = type_left if bom_right else type_right
            return {"note": "Only the %s side has a %s bill of material; there "
                            "is nothing to compare at this level." % (side, missing),
                    "components": []}

        # An assembly that contains itself would walk for ever. Real data does
        # this after a bad import, so the walk stops and says so.
        seen = set(seen or ())
        pair = (left.id, right.id)
        if pair in seen:
            return {"note": "Already compared higher up — cycle stopped.",
                    "components": []}
        seen.add(pair)

        entries = self._compare_entries(self._lines_by_code(bom_left),
                                        self._lines_by_code(bom_right))
        entries = self._flag_components(entries, type_left, type_right)

        components = []
        for entry in entries:
            component_left = entry.pop("_left", None)
            component_right = entry.pop("_right", None)
            if (depth > 1 and entry["has_components"]
                    and component_left and component_right):
                child = self._compare_node(component_left, type_left,
                                           component_right, type_right,
                                           depth - 1, seen)
                # Attached only when there is something to report: an identical
                # subassembly is recognised by has_components with no list.
                if self._is_different(child):
                    if child.get("note"):
                        entry["note"] = child["note"]
                    if child.get("summary"):
                        entry["summary"] = child["summary"]
                    entry["components"] = child["components"]
            components.append(entry)

        # Read in the order of the drawing: the balloon number is how an
        # engineer finds the row being talked about.
        components.sort(key=lambda row: (row.get("itemnum") or 9999,
                                         row["engineering_code"]))
        return {"summary": self._summarise(components), "components": components}

    @api.model
    def _flag_components(self, entries, type_left, type_right):
        """Say of each entry whether anything hangs below it.

        Both sides are asked in one query each rather than one per component:
        a thirty-row bill would otherwise cost sixty round trips to answer a
        question that is a single grouped count.
        """
        model = self.env["product.product"]
        lefts, rights = model.browse(), model.browse()
        for entry in entries:
            lefts |= entry.get("_left") or model.browse()
            rights |= entry.get("_right") or model.browse()

        boms_left = self._boms_by_template(lefts, type_left)
        boms_right = self._boms_by_template(rights, type_right)

        for entry in entries:
            component_left = entry.get("_left")
            component_right = entry.get("_right")
            entry["has_components"] = bool(
                (component_left and boms_left.get(
                    component_left.product_tmpl_id.id))
                or (component_right and boms_right.get(
                    component_right.product_tmpl_id.id)))
        return entries

    @api.model
    def _compare_entries(self, lines_left, lines_right):
        """Classify every code into one of the five states."""
        entries = []

        for code in sorted(set(lines_left) | set(lines_right)):
            left_entries = dict(lines_left.get(code, {}))
            right_entries = dict(lines_right.get(code, {}))

            # Exact matches first: same code, same revision.
            for revision in sorted(set(left_entries) & set(right_entries)):
                entry_left = left_entries.pop(revision)
                entry_right = right_entries.pop(revision)
                same_qty = entry_left["quantity"] == entry_right["quantity"]
                entry = {
                    "status": "unchanged" if same_qty else "qty_changed",
                    "engineering_code": code,
                    "engineering_revision": revision,
                    "name": entry_left["name"],
                    "engineering_state": entry_left["engineering_state"],
                    "itemnum": entry_left["itemnum"],
                    "_left": entry_left["product"],
                    "_right": entry_right["product"],
                }
                if same_qty:
                    entry["quantity"] = entry_left["quantity"]
                else:
                    entry["quantity_left"] = entry_left["quantity"]
                    entry["quantity_right"] = entry_right["quantity"]
                entries.append(entry)

            # What is left is the same code at different revisions on the two
            # sides: paired oldest to oldest so the report reads as one change
            # rather than a removal and an unrelated addition.
            # strict=False on purpose: when one side has more leftover revisions
            # than the other, the extras are not pairs — they fall through to
            # the one-sided states below.
            for entry_left, entry_right in zip(
                    [left_entries[r] for r in sorted(left_entries)],
                    [right_entries[r] for r in sorted(right_entries)],
                    strict=False):
                entries.append({
                    "status": "revision_changed",
                    "engineering_code": code,
                    "revision_left": entry_left["engineering_revision"],
                    "revision_right": entry_right["engineering_revision"],
                    "state_left": entry_left["engineering_state"],
                    "state_right": entry_right["engineering_state"],
                    "name": entry_right["name"],
                    "itemnum": entry_right["itemnum"] or entry_left["itemnum"],
                    "quantity_left": entry_left["quantity"],
                    "quantity_right": entry_right["quantity"],
                    "_left": entry_left["product"],
                    "_right": entry_right["product"],
                })
                left_entries.pop(entry_left["engineering_revision"], None)
                right_entries.pop(entry_right["engineering_revision"], None)

            for revision in sorted(left_entries):
                entries.append(self._one_sided(
                    "only_left", code, revision, left_entries[revision], "_left"))
            for revision in sorted(right_entries):
                entries.append(self._one_sided(
                    "only_right", code, revision, right_entries[revision], "_right"))

        return entries

    @api.model
    def _one_sided(self, status, code, revision, entry, side_key):
        """A component present on one side only.

        It still carries its product on that side, so has_components can say
        whether a whole subassembly is involved rather than a single part —
        which is the difference between a detail and a redesign.
        """
        return {
            "status": status,
            "engineering_code": code,
            "engineering_revision": revision,
            "name": entry["name"],
            "engineering_state": entry["engineering_state"],
            "itemnum": entry["itemnum"],
            "quantity": entry["quantity"],
            side_key: entry["product"],
        }

    @api.model
    def _summarise(self, components):
        counts = {}
        for component in components:
            counts[component["status"]] = counts.get(component["status"], 0) + 1
        return counts

    @api.model
    def _is_different(self, node):
        """Whether a compared branch holds anything worth reporting."""
        if node.get("note"):
            return True
        return any(component["status"] != "unchanged"
                   or component.get("components")
                   for component in node.get("components", []))
