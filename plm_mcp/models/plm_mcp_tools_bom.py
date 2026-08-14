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
"""What a product is made of.

Two kinds of question land here, and neither has an answer the database can give
on its own.

"Which components are ferrous" is a judgement about designations: the rows carry
EN-GJL-250 and CuSn12, and only a reader who knows that the first is cast iron
and the second bronze can answer. So each line carries its material and the
model decides — and says which materials it counted.

"Which are commercial parts" is worse, because there is no such field. What
exists is a set of signals that usually point the same way: the part can be
purchased, it has a supplier, it has no bill of material of its own, and
sometimes a category says so outright. Any one of them alone is wrong — a
machined part can be purchase_ok because it is subcontracted, and a bought
assembly can have a bill of material for documentation. So every line carries
the signals, the description tells the model how they usually combine, and the
answer is expected to state the criterion it used. A tool that decided this by
itself would be right in one shop and quietly wrong in the next.

The same principle runs through both: expose what is recorded, let the reader
classify, make the classification visible.
"""
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

MAX_DEPTH = 10


class PlmMcpToolsBom(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    # --------------------------------------------------------------- signals
    @api.model
    def _sourcing(self, product, has_bom):
        """The signals a reader needs to tell a bought part from a made one."""
        return {
            "purchase_ok": bool(product.purchase_ok),
            "suppliers": product.seller_ids.mapped("partner_id.name"),
            "has_bom": has_bom,
        }

    @api.model
    def _boms_by_template(self, products, bom_type=None):
        """Which of these products have a bill of material, in one query.

        Asked per line this would be one query per component; grouped, it is one
        for the whole level, which matters as soon as a bill has thirty rows.
        """
        if not products:
            return {}
        domain = [("product_tmpl_id", "in", products.product_tmpl_id.ids)]
        if bom_type:
            domain.append(("type", "=", bom_type))
        groups = self.env["mrp.bom"]._read_group(
            domain, groupby=["product_tmpl_id"], aggregates=["__count"])
        return {template.id: count for template, count in groups}

    @api.model
    def _used_in(self, product, bom_type=None):
        """The assemblies whose bill of material lists this part, one level up."""
        domain = [("product_id", "=", product.id)]
        if bom_type:
            domain.append(("type", "=", bom_type))
        lines = self.env["mrp.bom.line"].search(domain)
        parents = []
        for line in lines:
            parent = line.bom_id.product_tmpl_id.product_variant_id
            if not parent:
                continue
            parents.append({
                "engineering_code": parent.engineering_code,
                "engineering_revision": parent.engineering_revision,
                "bom_type": line.bom_id.type,
            })
        return parents

    # ------------------------------------------------------------------ tool
    @mcp_tool(
        "plm_bom",
        """
        The bill of material of a product: every component with its quantity,
        balloon number, material, category, and the signals that say whether it
        is bought or made.

        Answers "what is this made of", and questions about groups of components
        within it. Two of those need judgement rather than a filter:

        Ferrous, aluminium, plastic components: read the engineering_material of
        each line — EN-GJL-250 is cast iron, C45 and S235JR are steels, CuSn12
        is bronze, EN AW-6082 is aluminium — decide which ones the question
        covers, and tell the user which materials you counted.

        Commercial or bought parts: no field says so. Use the sourcing block on
        each line — purchase_ok, suppliers, has_bom. A part with no bill of
        material of its own, marked purchasable and carrying a supplier is
        normally a bought part; one with its own bill of material is normally
        made in house. The category may also say it outright. These signals
        disagree sometimes, so weigh them, and say which rule you applied.

        If the code is a part rather than an assembly the answer says so and
        names the assemblies that use it, so you can ask about those instead.
        """,
        properties={
            "code": {
                "type": "string",
                "description": "Exact engineering code of the product, "
                               "e.g. 'BRG-UNIT-001'.",
            },
            "revision": {
                "type": "integer",
                "description": "Which revision. Omit for the newest one.",
            },
            "bom_type": {
                "type": "string",
                "description": "'normal' for the manufacturing bill, 'spbom' for "
                               "the spare parts one. Default 'normal'.",
            },
            "depth": {
                "type": "integer",
                "description": "How many levels to expand. Default 1, which is "
                               "the direct components. Raise it to walk down the "
                               "whole structure.",
            },
        },
        required=["code"],
    )
    def plm_bom(self, code=None, revision=None, bom_type="normal", depth=1):
        product = self._find_part(code, revision)
        if not product:
            raise UserError(self._no_part(code, revision))

        bom_type = (bom_type or "normal").strip()
        depth = max(1, min(int(depth or 1), MAX_DEPTH))
        return self._bom_node(product, bom_type, depth)

    # ------------------------------------------------------------- expansion
    @api.model
    def _bom_node(self, product, bom_type, depth, seen=None):
        """One level of a bill of material, with its children under it."""
        node = self._part_summary(product)
        node["bom_type"] = bom_type

        bom = self.env["mrp.bom"].search([
            ("product_tmpl_id", "=", product.product_tmpl_id.id),
            ("type", "=", bom_type),
        ], limit=1)

        if not bom:
            # Not an assembly. Saying only "no components" would read as "it is
            # empty"; naming where it is used turns a dead end into the next
            # question, which is usually the one that was really meant. It stays
            # a pointer, not an answer: which revision is used where is
            # plm_where_used's job, and duplicating it here would give two
            # places that answer the same question differently.
            node.update({
                "has_bom": False,
                "lines": [],
                "used_in": self._used_in(product),
                "note": _(
                    "This code has no %(type)s bill of material — it is a part, "
                    "not an assembly. This answer describes revision "
                    "%(revision)s; use plm_where_used to see where each revision "
                    "is used."
                ) % {"type": bom_type, "revision": product.engineering_revision},
            })
            return node

        # A part that contains itself, directly or through a chain, would walk
        # forever. Real data does this after a bad import.
        seen = set(seen or ())
        if product.id in seen:
            node.update({"has_bom": True, "lines": [],
                         "note": _("Already expanded higher up — cycle stopped.")})
            return node
        seen.add(product.id)

        components = bom.bom_line_ids.mapped("product_id")
        child_boms = self._boms_by_template(components, bom_type)

        lines = []
        for line in bom.bom_line_ids.sorted(lambda row: (row.itemnum or 0, row.id)):
            component = line.product_id
            has_bom = bool(child_boms.get(component.product_tmpl_id.id))
            entry = self._part_summary(component)
            entry.update({
                "itemnum": line.itemnum or None,
                "quantity": line.product_qty,
                "uom": line.product_uom_id.name,
                "sourcing": self._sourcing(component, has_bom),
            })
            if depth > 1 and has_bom:
                entry["components"] = self._bom_node(
                    component, bom_type, depth - 1, seen)["lines"]
            lines.append(entry)

        node.update({
            "has_bom": True,
            "bom_quantity": bom.product_qty,
            "lines": lines,
        })
        return node
