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
"""The vocabulary bridge.

An engineer asks for "the iron parts". The database holds EN-GJL-250, S235JR,
39NiCrMo3 — normative designations, typed by the CAD into a free-text field. No
amount of searching for "iron" finds them, and a model that guesses a term and
reports nothing has given a confident wrong answer, which is worse than saying
it cannot tell.

So these tools hand over the designations actually in use, with how many parts
carry each. The model reads the list, recognises which entries answer the
question, and searches for those — then says which ones it counted, so the
person can disagree. That last part matters: "in iron" is an interpretation,
not a filter, and grey cast iron is iron to a designer and not to a buyer.

One tool per vocabulary rather than one tool with a switch. What routes a model
to the right tool is the description, and three separate descriptions can each
say what that vocabulary contains and when it answers a question — a single
description covering three would have to speak in generalities, which is
exactly where a model starts guessing.
"""
import logging

from odoo import api, models

from .plm_mcp_tool import mcp_tool

_logger = logging.getLogger(__name__)

MAX_VALUES = 200

# The shared tail of every description: the same warning applies to all three,
# and repeating it per tool keeps each one self-contained for the model, which
# reads them separately and never sees them side by side.
HOW_TO_USE = """
        Two lists come back: title_block is the text written on the drawing and
        read on the shop floor, catalogue is the structured entry. Which of the
        two is filled depends on how the part was created, so consider both.
        Read the list, decide which entries answer the question, pass them to
        plm_find_part — and tell the user which ones you counted, because that
        judgement is yours and they may disagree with it.
"""


class PlmMcpToolsVocabulary(models.AbstractModel):
    _inherit = "plm.mcp.tool"

    # ----------------------------------------------------------------- tools
    @mcp_tool(
        "plm_list_materials",
        """
        The raw materials actually used on the engineering parts, with how many
        parts carry each one — EN-GJL-250, S235JR, 39NiCrMo3 and the like.

        Call this before searching by material: the field is free text written
        by the CAD and holds normative designations, so a plain-language term
        such as "iron", "steel" or "plastic" matches nothing on its own.
        """ + HOW_TO_USE,
    )
    def plm_list_materials(self):
        return self._vocabulary("material", "engineering_material", "tmp_material")

    @mcp_tool(
        "plm_list_finishings",
        """
        The surface finishings actually specified on the engineering parts, with
        how many parts carry each one — anodising, galvanising, painting,
        polishing and the like, as written on the drawing.

        Call this before searching by surface finishing: the field is free text
        written by the CAD, so a plain-language term rarely matches what is
        actually recorded.
        """ + HOW_TO_USE,
    )
    def plm_list_finishings(self):
        return self._vocabulary("surface", "engineering_surface", "tmp_surface")

    @mcp_tool(
        "plm_list_treatments",
        """
        The thermal treatments actually specified on the engineering parts, with
        how many parts carry each one — hardening, tempering, case hardening,
        stress relieving and the like, as written on the drawing.

        Call this before searching by treatment: the field is free text written
        by the CAD, so a plain-language term rarely matches what is actually
        recorded.
        """ + HOW_TO_USE,
    )
    def plm_list_treatments(self):
        return self._vocabulary("treatment", "engineering_treatment", "tmp_treatment")

    # ------------------------------------------------------------- gathering
    @api.model
    def _vocabulary(self, kind, text_field, catalogue_field):
        return {
            "kind": kind,
            "title_block": self._vocabulary_from_text(text_field),
            "catalogue": self._vocabulary_from_catalogue(catalogue_field),
        }

    @api.model
    def _vocabulary_from_text(self, field_name):
        """Distinct values of a CAD text field, with a count each.

        Grouped on product.template because that is where the field is stored;
        grouping on the variant would go through the delegation and cannot be
        done in SQL. Parts without an engineering code are excluded, so a
        catalogue of sellable articles does not pollute the vocabulary.
        """
        groups = self.env["product.template"]._read_group(
            [(field_name, "!=", False), ("engineering_code", "!=", False)],
            groupby=[field_name],
            aggregates=["__count"],
        )
        values = [{"value": value, "parts": count} for value, count in groups if value]
        # Most used first: it answers the question nine times out of ten, and a
        # model reads the head of a list more carefully than its tail.
        values.sort(key=lambda row: (-row["parts"], row["value"]))
        return self._capped(values)

    @api.model
    def _vocabulary_from_catalogue(self, field_name):
        """Catalogue entries in use, with their description and a count."""
        groups = self.env["product.product"]._read_group(
            [(field_name, "!=", False), ("engineering_code", "!=", False)],
            groupby=[field_name],
            aggregates=["__count"],
        )
        values = []
        for record, count in groups:
            if not record:
                continue
            values.append({
                "name": record.name,
                "description": record.description or None,
                "parts": count,
            })
        values.sort(key=lambda row: (-row["parts"], row["name"] or ""))
        return self._capped(values)

    @api.model
    def _capped(self, values):
        """Cut a long vocabulary, and say so rather than truncating in silence."""
        if len(values) <= MAX_VALUES:
            return values
        _logger.info("plm_mcp: vocabulary cut at %s of %s values",
                     MAX_VALUES, len(values))
        return values[:MAX_VALUES] + [{"note": "list cut at %s values, "
                                       "most used first" % MAX_VALUES}]
