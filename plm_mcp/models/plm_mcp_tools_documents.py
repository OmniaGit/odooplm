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
"""What is documented in a structure, and what is not.

The question this exists for is asked before a product goes to production:
which components still have no drawing. It is not a document listing — it is a
completeness check, and the useful answer is the short list of gaps, not the
long list of what is fine.

Which gaps count depends on a distinction the database does not record: a part
made to drawing, in house or by a subcontractor, needs a drawing; a catalogue
item bought off the shelf — a screw, a bearing, a seal — does not, and listing
those as missing would bury the real gaps under noise. There is no field that
says which is which, so every row carries the signals that usually decide it:
whether anyone modelled it in CAD, whether it has a bill of material of its own,
whether it is flagged for purchase and has a supplier, and its category. The
strongest of those is the CAD model — someone modelling a part is someone
designing it — and the weakest is the purchase flag, which in many databases is
set on everything.

The reader combines them and says which rule was applied. A tool that decided
by itself would be right in one company and quietly wrong in the next.
"""
import logging

from odoo import api, models
from odoo.exceptions import UserError

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

MAX_DEPTH = 10


class PlmMcpToolsDocuments(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    @mcp_tool(
        "plm_documents",
        """
        The documents of every component in a structure, and what is missing.

        Answers the completeness questions asked before production: which
        components have no drawing, which have a drawing but no printable PDF,
        which have no CAD model at all. Set missing to 'drawing', 'model' or
        'printout' to get only the components that lack it — that is usually the
        question, and it keeps the answer to the gaps.

        Reading the result: has_drawing is the sheet, has_model the CAD model,
        has_printout the printable PDF attached to a sheet. A component with a
        model and no drawing is a part somebody modelled and nobody drew, which
        is the classic gap.

        The two are recognised by the document link, not by the file type: in
        this suite a model and its sheet are joined by a LyTree relation, the
        model on one end and the drawing on the other. The type of the file is
        used as a fallback, because it depends on which CAD wrote it and is
        wrong often enough not to be trusted on its own.

        Not every missing drawing is a gap. A catalogue part bought off the
        shelf needs no drawing of yours; a part made to drawing does. Use the
        signals on each row to tell them apart — has_model and has_own_bom
        point at a part you design, purchase_ok with a named supplier and no CAD
        model points at something you buy, and the category may say it outright.
        Say which rule you applied when you report the count, because the person
        reading may draw the line elsewhere.
        """,
        properties={
            "code": {
                "type": "string",
                "description": "Engineering code at the top of the structure, "
                               "e.g. 'LSU-100'.",
            },
            "revision": {
                "type": "integer",
                "description": "Revision of that code. Omit for the newest.",
            },
            "bom_type": {
                "type": "string",
                "description": "'normal' or 'spbom'. Default 'normal'.",
            },
            "depth": {
                "type": "integer",
                "description": "How many levels down to walk. Default 10.",
            },
            "missing": {
                "type": "string",
                "enum": ["drawing", "model", "printout"],
                "description": "Return only the components that lack this.",
            },
        },
        required=["code"],
    )
    def plm_documents(self, code=None, revision=None, bom_type="normal",
                      depth=MAX_DEPTH, missing=None):
        product = self._find_part(code, revision)
        if not product:
            raise UserError(self._no_part(code, revision))

        bom_type = (bom_type or "normal").strip()
        depth = max(1, min(int(depth or MAX_DEPTH), MAX_DEPTH))
        missing = (missing or "").strip().lower() or None

        components = self._collect_structure(product, bom_type, depth)

        # Everything the rows need, asked once for the whole structure rather
        # than once per component: three queries instead of three per part.
        documents = self.env["ir.attachment"].browse()
        for component in components.values():
            documents |= component.linkeddocuments
        context = {
            "printout": self._printout_ids(documents),
            "models": self._lytree_models(documents),
            "drawings": self._lytree_drawings(documents),
        }

        rows = [self._document_row(component, bom_type, context)
                for component in components.values()]

        totals = {
            "components": len(rows),
            "without_drawing": len([r for r in rows if not r["has_drawing"]]),
            "without_model": len([r for r in rows if not r["has_model"]]),
            "without_printout": len([r for r in rows if not r["has_printout"]]),
        }

        if missing:
            key = {"drawing": "has_drawing", "model": "has_model",
                   "printout": "has_printout"}[missing]
            rows = [row for row in rows if not row[key]]

        rows.sort(key=lambda row: row["engineering_code"] or "")
        return {
            "top": self._part_summary(product),
            "bom_type": bom_type,
            "filter": {"missing": missing} if missing else None,
            "totals": totals,
            "components": rows,
        }

    # ------------------------------------------------------------ gathering
    @api.model
    def _collect_structure(self, product, bom_type, depth, collected=None):
        """Every distinct part in the structure, the top one included.

        Keyed by database id, so a component used in three places is one row
        and not three: the question is whether it is documented, and that does
        not change with how often it is used.
        """
        collected = {} if collected is None else collected
        if product.id in collected:
            return collected
        collected[product.id] = product

        if depth <= 1:
            return collected
        bom = self._bom_of(product, bom_type)
        for line in bom.bom_line_ids:
            self._collect_structure(line.product_id, bom_type, depth - 1, collected)
        return collected

    @api.model
    def _lytree_models(self, documents):
        """Documents that are the model end of a model-to-drawing link."""
        if not documents:
            return set()
        relations = self.env["ir.attachment.relation"].search([
            ("link_kind", "=", "LyTree"), ("parent_id", "in", documents.ids)])
        return set(relations.mapped("parent_id").ids)

    @api.model
    def _lytree_drawings(self, documents):
        """Documents that are the drawing end of a model-to-drawing link."""
        if not documents:
            return set()
        relations = self.env["ir.attachment.relation"].search([
            ("link_kind", "=", "LyTree"), ("child_id", "in", documents.ids)])
        return set(relations.mapped("child_id").ids)

    @api.model
    def _document_row(self, product, bom_type, context):
        """One component: what it has, what it lacks, and what kind of part it is.

        A drawing is recognised by the LyTree link first and by the document
        type second. The link is what the CAD client writes when it saves a
        sheet against its model, and it holds whatever the file happens to be —
        the type depends on which CAD produced it, and in a database where the
        native files were replaced by neutral formats it is simply wrong.
        """
        documents = product.linkeddocuments
        by_type = {}
        for document in documents:
            by_type.setdefault(document.document_type or "unset", []).append(document)

        drawings = [d for d in documents
                    if d.id in context["drawings"] or d.document_type == "2d"]
        models = [d for d in documents
                  if d.id in context["models"] or d.document_type == "3d"]

        row = self._part_summary(product)
        row.update({
            "has_drawing": bool(drawings),
            "has_model": bool(models),
            # Asked of the sheets only: a PDF hanging off a model is not what
            # anyone means by "the drawing has a printout".
            "has_printout": any(d.id in context["printout"] for d in drawings),
            "documents": {
                doc_type: len(items) for doc_type, items in sorted(by_type.items())
            },
            "signals": {
                "has_model": bool(models),
                "has_own_bom": bool(self._bom_of(product, bom_type)),
                "purchase_ok": bool(product.purchase_ok),
                "suppliers": product.seller_ids.mapped("partner_id.name"),
            },
        })
        return row
