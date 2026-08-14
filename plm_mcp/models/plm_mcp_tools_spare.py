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
"""The spare parts of a product, as a list someone can order from.

A spare parts list is read differently from a bill of material. The engineer
reads a structure; whoever orders a replacement reads a list — code, what it is,
how many, and the balloon number to quote. So this returns rows, not a tree.

Flattening a structure usually destroys information, and here it would: in a
three level product the item actually sold as a spare may be the grandchild, or
the sub-assembly, or both, and a flat list that dropped the levels could not
tell those apart. So every row carries where it sits — its level, its parent,
and the path from the top — which makes the hierarchy recoverable from the list
without asking for it again.

Two flags carry the rest of the meaning. has_spare_children says the item is
offered whole *and* broken down further, so a customer can order the assembly or
its wear parts. is_kit says the opposite: the item is sold as one package, and
the rows underneath it are what the package contains rather than things to order
separately. A kit is a property of the bill — a bill of type phantom — not of
the product, so it is read from the structure and not from a flag someone may
have set for another purpose.

Everything in the list is offered as a spare — that is what being in a spare
parts bill means. What varies is at which level, and that is what the rows say.
"""
import logging

from odoo import api, models
from odoo.exceptions import UserError

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

MAX_DEPTH = 10
SPARE_TYPE = "spbom"
KIT_TYPE = "phantom"


class PlmMcpToolsSpare(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    @mcp_tool(
        "plm_spare_parts",
        """
        The spare parts list of a product: every item offered as a replacement,
        flattened into rows with the position number to quote when ordering.

        Use this for anything about spares, replacements, wear parts or the
        spare parts manual. It reads the spare parts bill, which is a different
        structure from the manufacturing one — a product's spares are not simply
        its components: the base plate and the shaft of a machine are made but
        never sold as spares, while a bushing that wears out is.

        Every row says where it sits: level, parent and path from the top. Read
        those before answering "which spare belongs to what", because the item
        actually sold may be a sub-assembly, one of its parts, or both.

        Two flags change the meaning of a row. has_spare_children means the item
        is offered whole and also broken down, so either can be ordered. is_kit
        means it is sold as one package — the rows below a kit come with it and
        are not ordered separately.

        quantity is how many are used in the parent; total_quantity is how many
        are in the whole product, the quantities multiplied down the path. Quote
        the position number and the code, not the internal id.
        """,
        properties={
            "code": {
                "type": "string",
                "description": "Engineering code of the product, e.g. 'LSU-100'.",
            },
            "revision": {
                "type": "integer",
                "description": "Revision. Omit for the newest.",
            },
            "depth": {
                "type": "integer",
                "description": "How many levels to walk. Default 10.",
            },
        },
        required=["code"],
    )
    def plm_spare_parts(self, code=None, revision=None, depth=MAX_DEPTH):
        product = self._find_part(code, revision)
        if not product:
            raise UserError(self._no_part(code, revision))

        depth = max(1, min(int(depth or MAX_DEPTH), MAX_DEPTH))
        if not self._bom_of(product, SPARE_TYPE):
            # Said plainly rather than returned as an empty list: "no spare
            # parts list exists for this product" and "this product has no
            # spares" are different facts, and the second one would be a
            # conclusion nobody has drawn.
            return {
                "top": self._part_summary(product),
                "has_spare_list": False,
                "rows": [],
                "note": "This product has no spare parts bill of material. It "
                        "may still be a spare itself — check the products that "
                        "use it.",
            }

        rows = []
        self._collect_spares(product, depth, [product.engineering_code], 1.0, rows)
        return {
            "top": self._part_summary(product),
            "has_spare_list": True,
            "count": len(rows),
            "rows": rows,
        }

    # ------------------------------------------------------------ the walk
    @api.model
    def _collect_spares(self, product, depth, path, multiplier, rows, seen=None):
        """Walk the spare structure, writing one row per item as it goes."""
        seen = set(seen or ())
        if product.id in seen:
            return
        seen = seen | {product.id}

        bom = self._bom_of(product, SPARE_TYPE)
        if not bom or depth < 1:
            return

        for line in bom.bom_line_ids.sorted(lambda row: (row.itemnum or 0, row.id)):
            component = line.product_id
            child_bom = self._bom_of(component, SPARE_TYPE)
            total = multiplier * line.product_qty

            row = self._part_summary(component)
            row.update({
                "level": len(path),
                "parent": path[-1],
                "path": " / ".join(path),
                "itemnum": line.itemnum or None,
                "quantity": line.product_qty,
                # Multiplied down the chain: a bushing used once in a unit that
                # goes into the machine twice is two bushings in the machine,
                # and that is the number a customer needs.
                "total_quantity": total,
                "has_spare_children": bool(child_bom),
                "is_kit": self._is_kit(component),
            })
            rows.append(row)

            if child_bom and depth > 1:
                self._collect_spares(
                    component, depth - 1, path + [component.engineering_code],
                    total, rows, seen)

    @api.model
    def _is_kit(self, product):
        """Whether this item is sold as one package.

        A kit is a bill of type phantom, which is Odoo's way of saying the
        product is not built but handed over as its components. The flag that
        exists on the product is used when generating such a bill, so reading it
        would answer a different question — what someone intended — instead of
        what the structure actually says.
        """
        return bool(self._bom_of(product, KIT_TYPE))
