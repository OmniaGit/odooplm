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
"""Tools that answer questions about parts.

Everything here runs in the environment of the API key's user, so the searches
below are already filtered by the PLM record rules — a part the person cannot
see is not in the result, and nothing extra had to be written to make that true.

Results are keyed by engineering code and revision rather than by database id.
An id means nothing to a model, cannot be checked against a drawing, and would
be the wrong thing for it to repeat back to an engineer.

Two shapes, on purpose. A summary is what a part looks like when it is merely
*named* — a row in a search, a line in a where-used tree — and carries the
material and the category, because "what is it made of" and "what kind of part
is it" are what an engineer reads first. The detail is for when the part is the
subject of the question, and holds the rest: the standard description with its
feature values, why it was revised, where it came from, what is attached to it.
Putting the detail in every row would make a twenty-node tree unreadable and
cost tokens for fields nobody asked about.
"""
import logging

from odoo import api, models
from odoo.exceptions import UserError

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


class PlmMcpToolsPart(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    # --------------------------------------------------------------- lookup
    @api.model
    def _find_part(self, code, revision=None):
        """The part behind a code, at a revision or at the latest one.

        Shared by every tool that takes a code, so they all resolve it the same
        way: matched case-insensitively, because a code copied out of a drawing
        or an email rarely keeps the casing of the database, and refusing on
        that would be a puzzle for the caller rather than an answer.
        """
        code = (code or "").strip()
        if not code:
            return self.env["product.product"]
        domain = [("engineering_code", "=ilike", code)]
        if revision is not None:
            domain.append(("engineering_revision", "=", int(revision)))
        return self.env["product.product"].search(
            domain, order="engineering_revision desc", limit=1)

    @api.model
    def _revision_history(self, code):
        """Every revision of a code, newest first, as revision and state."""
        products = self.env["product.product"].search(
            [("engineering_code", "=ilike", (code or "").strip())],
            order="engineering_revision desc")
        return [{
            "engineering_revision": product.engineering_revision,
            "engineering_state": product.engineering_state,
        } for product in products]

    # ---------------------------------------------------------------- shapes
    @api.model
    def _part_summary(self, product):
        """A part as it appears when it is named in a list."""
        return {
            "engineering_code": product.engineering_code,
            "engineering_revision": product.engineering_revision,
            "engineering_revision_letter": product.engineering_revision_letter or None,
            "engineering_state": product.engineering_state,
            "name": product.name,
            "engineering_material": product.engineering_material or None,
            # The full path, not the leaf: "All / Mechanical / Machined" says
            # more than "Machined", and the model has no tree to consult.
            "category": product.categ_id.complete_name or None,
        }

    @api.model
    def _part_detail(self, product):
        """Everything an engineer would want when asking about one part."""
        detail = self._part_summary(product)
        detail.update({
            "engineering_surface": product.engineering_surface or None,
            "engineering_treatment": product.engineering_treatment or None,
            # The catalogue entries behind the CAD text, where they are filled.
            # The Char fields come from the drawing title block and are what the
            # shop floor reads; these are the structured values, and they can
            # disagree — worth showing both rather than choosing one.
            "raw_material": product.tmp_material.display_name or None,
            "surface_finishing": product.tmp_surface.display_name or None,
            "thermal_treatment": product.tmp_treatment.display_name or None,
            "standard_description": product.std_description.display_name or None,
            "features": self._part_features(product),
            "modification_description": product.desc_modify or None,
            "generated_from": product.source_product.engineering_code or None,
            "tags": product.product_tag_ids.mapped("name"),
            "created_on": product.create_date,
            "modified_on": product.write_date,
            "documents": self._part_documents(product),
        })
        return detail

    @api.model
    def _part_features(self, product):
        """The three standard-description slots, as label and value pairs.

        Returned paired rather than as six flat fields: "Length: 260 mm" is
        something a model can put in a sentence, std_umc1 / std_value1 is not.
        Empty slots are dropped — an unfilled feature is not information.
        """
        features = []
        for label, value in (
            (product.std_umc1, product.std_value1),
            (product.std_umc2, product.std_value2),
            (product.std_umc3, product.std_value3),
        ):
            if label or value:
                features.append({"label": label or None, "value": value})
        return features

    @api.model
    def _part_documents(self, product):
        """The engineering documents attached to the part."""
        documents = product.linkeddocuments
        with_printout = self._printout_ids(documents)
        checked_out = self._checked_out_ids(documents)
        return [{
            "name": document.name,
            "document_type": document.document_type,
            "engineering_code": document.engineering_code,
            "engineering_revision": document.engineering_revision,
            "engineering_state": document.engineering_state,
            # The printable sheet is a binary field, so it shows up neither in
            # the name nor in the type: without this flag a reader concludes
            # there is no PDF, which is the opposite of the truth.
            "has_printout": document.id in with_printout,
            "is_checked_out": document.id in checked_out,
        } for document in documents]

    @api.model
    def _printout_ids(self, documents):
        """Which of these documents carry a printable PDF.

        printout is a binary field, so Odoo keeps its content in a separate
        attachment row rather than in a column. Asked through the field it would
        load every PDF into memory to answer a yes or no; asked as a search over
        those rows it is one query and no payload.

        Read with sudo because those rows are plumbing, not documents in their
        own right — what is revealed is a boolean about a document the caller
        can already see.
        """
        if not documents:
            return set()
        rows = self.env["ir.attachment"].sudo().search_read([
            ("res_model", "=", "ir.attachment"),
            ("res_field", "=", "printout"),
            ("res_id", "in", documents.ids),
        ], ["res_id"])
        return {row["res_id"] for row in rows}

    @api.model
    def _checked_out_ids(self, documents):
        """Which of these documents someone is holding open in a CAD session."""
        if not documents:
            return set()
        rows = self.env["plm.checkout"].sudo().search_read(
            [("documentid", "in", documents.ids)], ["documentid"])
        return {row["documentid"][0] for row in rows}

    # ----------------------------------------------------------------- tools
    @mcp_tool(
        "plm_find_part",
        """
        Find engineering parts by code, name, material, surface finishing,
        thermal treatment, category or tag. Returns each part's engineering
        code, revision, state, material and category.

        Use this first whenever the user names a part in words or gives a
        partial code: every other PLM tool takes an exact engineering code, and
        this is how you get one. Use the filters to answer questions about
        groups of parts — everything made of a given material, everything in a
        category. Material, surface and treatment are free text written by the
        CAD: call plm_list_materials, plm_list_finishings or plm_list_treatments
        first to see the designations actually in use, rather than guessing a
        term that will match nothing.
        """,
        properties={
            "query": {
                "type": "string",
                "description": "Part of an engineering code or of a name, "
                               "e.g. 'BRG-HSG' or 'bearing housing'.",
            },
            "material": {
                "type": "string",
                "description": "Matches the raw material, e.g. 'EN-GJL-250'. "
                               "Free text: call plm_list_materials to see what exists.",
            },
            "surface": {
                "type": "string",
                "description": "Matches the surface finishing.",
            },
            "treatment": {
                "type": "string",
                "description": "Matches the thermal treatment.",
            },
            "category": {
                "type": "string",
                "description": "Matches the product category path, "
                               "e.g. 'Mechanical' or 'All / Mechanical / Machined'.",
            },
            "tag": {
                "type": "string",
                "description": "Matches one of the product tags.",
            },
            "latest_only": {
                "type": "boolean",
                "description": "Only the highest revision of each code. "
                               "Default true; set false to see the history.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum parts to return, 1 to 100. Default 20.",
            },
        },
        required=[],
    )
    def plm_find_part(self, query=None, material=None, surface=None,
                      treatment=None, category=None, tag=None,
                      latest_only=True, limit=DEFAULT_LIMIT):
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))

        # engineering_code != False keeps ordinary products out: a name or
        # category search would otherwise return sellable articles that have
        # nothing to do with the engineering data being asked about.
        domain = [("engineering_code", "!=", False)]
        if query:
            domain += ["|", ("engineering_code", "ilike", query.strip()),
                       ("name", "ilike", query.strip())]
        if material:
            # Either the title-block text or the catalogue entry: which of the
            # two is filled varies by how the part was created.
            domain += ["|", ("engineering_material", "ilike", material.strip()),
                       ("tmp_material.name", "ilike", material.strip())]
        if surface:
            domain += ["|", ("engineering_surface", "ilike", surface.strip()),
                       ("tmp_surface.name", "ilike", surface.strip())]
        if treatment:
            domain += ["|", ("engineering_treatment", "ilike", treatment.strip()),
                       ("tmp_treatment.name", "ilike", treatment.strip())]
        if category:
            domain.append(("categ_id.complete_name", "ilike", category.strip()))
        if tag:
            domain.append(("product_tag_ids.name", "ilike", tag.strip()))

        if len(domain) == 1 and not any((query, material, surface, treatment,
                                         category, tag)):
            # No criterion at all would walk the whole catalogue and hand back
            # an arbitrary slice of it, which reads as an answer and is not one.
            return self._tool_error_payload()

        # Highest revision first, so keeping the first row per code below is the
        # same thing as keeping the latest revision.
        products = self.env["product.product"].search(
            domain, order="engineering_code asc, engineering_revision desc",
            limit=None if latest_only else limit,
        )

        if latest_only:
            seen, latest = set(), self.env["product.product"]
            for product in products:
                if product.engineering_code in seen:
                    continue
                seen.add(product.engineering_code)
                latest |= product
                if len(latest) >= limit:
                    break
            products = latest

        return {
            "count": len(products),
            "truncated": len(products) >= limit,
            "parts": [self._part_summary(product) for product in products],
        }

    @api.model
    def _tool_error_payload(self):
        return {
            "count": 0,
            "parts": [],
            "note": "Give at least one criterion: a query, a material, a "
                    "surface, a treatment, a category or a tag.",
        }

    @mcp_tool(
        "plm_part_detail",
        """
        Everything recorded about one part: material, surface finishing and
        thermal treatment, the standard description with its feature values, why
        it was last revised, which part it was generated from, its tags and
        category, and the engineering documents attached to it.

        Takes an exact engineering code — use plm_find_part when you only have a
        name or a fragment. Without a revision you get the newest one, and the
        answer always says which revision it describes and which others exist,
        so you never report a released part's data when the user is asking about
        a draft, or the other way round.

        modification_description says what *this* revision changed with respect
        to the one before it. On a first revision it is empty because there is
        no earlier one to differ from — is_first_revision tells you that, and it
        is the difference between "this is the original issue, there is nothing
        to report" and "the information is missing". previous_revision names
        what this one came after, and is what to compare against when the next
        question is what actually changed.
        """,
        properties={
            "code": {
                "type": "string",
                "description": "Exact engineering code, e.g. 'BRG-HSG-001'.",
            },
            "revision": {
                "type": "integer",
                "description": "Which revision. Omit for the newest one.",
            },
        },
        required=["code"],
    )
    def plm_part_detail(self, code=None, revision=None):
        product = self._find_part(code, revision)
        if not product:
            # Raised, not returned: _call_tool turns this into an error result
            # the model reads and can act on, rather than a transport failure.
            raise UserError(self._no_part(code, revision))

        detail = self._part_detail(product)
        history = self._revision_history(product.engineering_code)
        detail["is_latest"] = bool(history) and (
            history[0]["engineering_revision"] == product.engineering_revision)

        # An empty modification description on a first revision is an answer,
        # not a gap: there is no earlier revision for it to describe. Saying so
        # here keeps the reader from reporting missing data.
        earlier = [row["engineering_revision"] for row in history
                   if row["engineering_revision"] < product.engineering_revision]
        detail["is_first_revision"] = not earlier
        detail["previous_revision"] = max(earlier) if earlier else None
        # The other revisions travel with the answer: "is this the current one"
        # is the next question every time, and it costs one search to pre-empt
        # a second round trip.
        detail["revisions"] = history
        return detail
