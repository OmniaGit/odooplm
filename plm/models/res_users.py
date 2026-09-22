# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

"""
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
from odoo import api, fields, models

from odoo.addons.plm.models.res_partner import PORTAL_ACCESS_LEVELS

# How far a bill of materials is walked when a portal user browses what is
# under what they bought: a guard against a loop in the data, not a rule.
PORTAL_EXPLOSION_DEPTH = 20


class ResUsers(models.Model):
    _inherit = "res.users"

    plm_portal_access = fields.Selection(
        [("inherit", "From the partner")] + PORTAL_ACCESS_LEVELS,
        string="PLM Portal Access",
        default="inherit",
        help="Left on 'From the partner' this user gets what the partner "
        "allows; any other value is this user's own, so one user of a customer "
        "or a vendor can be given more, or nothing at all.",
    )

    def _plm_portal_access_level(self):
        """What this user may do with the PLM documents they reach from the
        portal: 'none', 'view' or 'markup'."""
        self.ensure_one()
        if self.plm_portal_access and self.plm_portal_access != "inherit":
            return self.plm_portal_access
        partner = self.sudo().partner_id.commercial_partner_id
        return partner.plm_portal_access or "none"

    def _plm_portal_can_markup(self):
        self.ensure_one()
        return self._plm_portal_access_level() == "markup"

    def _plm_portal_products(self):
        """The products this user reaches from the portal.

        The orders are searched as the user, so it is Odoo's own portal rules
        that say which ones are theirs; everything read afterwards is read with
        sudo, because the portal has no access to products, bills of materials
        or documents. A revision is a product of its own, so a line pins the
        very revision that was sold or bought: a revision obsoleted later stays
        visible to whoever bought it.
        """
        self.ensure_one()
        products = self.env["product.product"].sudo().browse()
        if self._plm_portal_access_level() == "none":
            return products
        products = self._plm_portal_ordered_products()
        return (
            products
            | self._plm_portal_spare_products(products)
            | self._plm_portal_subcontracted_products()
        )

    def _plm_portal_ordered_products(self):
        """What is on the order lines this user may read: sold to a customer,
        bought from a vendor. A module without sale or purchase installed
        simply has nothing to add here."""
        self.ensure_one()
        products = self.env["product.product"].sudo().browse()
        for model in ("sale.order.line", "purchase.order.line"):
            if model not in self.env:
                continue
            lines = (
                self.env[model]
                .with_user(self)
                .search([("product_id", "!=", False)])
            )
            products |= lines.sudo().product_id
        return products

    def _plm_portal_spare_products(self, products):
        """The spare parts of what was bought, when the partner allows it: the
        components of the spare bills of materials, at every level."""
        self.ensure_one()
        partner = self.sudo().partner_id.commercial_partner_id
        if not partner.plm_portal_spares:
            return self.env["product.product"].sudo().browse()
        return self._plm_portal_explode(products, [("type", "=", "spbom")])

    def _plm_portal_subcontracted_products(self):
        """What a subcontractor makes: the components, at every level, of the
        bills of materials that name this partner as one.

        mrp_subcontracting is where Odoo keeps that link; without that module
        there is no such thing as a subcontractor, and nothing is added.
        """
        self.ensure_one()
        boms = self.env["mrp.bom"].sudo()
        if "subcontractor_ids" not in boms._fields:
            return self.env["product.product"].sudo().browse()
        partner = self.sudo().partner_id.commercial_partner_id
        subcontracted = boms.search(
            [("subcontractor_ids.commercial_partner_id", "in", partner.ids)]
        )
        if not subcontracted:
            return self.env["product.product"].sudo().browse()
        components = subcontracted.bom_line_ids.product_id
        return components | self._plm_portal_explode(components, [])

    def _plm_portal_explode(self, products, bom_domain):
        """Every product under *products*, following the bills of materials
        that match *bom_domain*, level by level."""
        boms = self.env["mrp.bom"].sudo()
        found = self.env["product.product"].sudo().browse()
        frontier = products.sudo()
        for _depth in range(PORTAL_EXPLOSION_DEPTH):
            if not frontier:
                break
            structures = boms.search(
                [("product_tmpl_id", "in", frontier.product_tmpl_id.ids)]
                + bom_domain
            )
            frontier = structures.bom_line_ids.product_id - found - products
            found |= frontier
        return found

    def _plm_portal_documents(self, products=None):
        """The PLM documents this user reaches from the portal, each with what
        they may get of it (see _plm_portal_document_policy)."""
        self.ensure_one()
        if products is None:
            products = self._plm_portal_products()
        documents = products.sudo().linkeddocuments
        return documents.filtered(lambda doc: self._plm_portal_document_policy(doc))

    @api.model
    def _plm_portal_document_policy(self, document):
        """What a portal user may get of a PLM document: 'view3d' for the file
        the 3D viewer shows, 'pdf' for the printout of a drawing.

        The native CAD file is never one of them. Override this to narrow it
        for a customer who asks, or to widen it to another format.
        """
        allowed = set()
        name = (document.sudo().name or "").lower()
        if name.endswith(".3mf"):
            allowed.add("view3d")
        if document.sudo().document_type == "2d" and document.sudo().printout:
            allowed.add("pdf")
        return allowed

    def _plm_portal_may(self, document, purpose):
        """Whether this user may get *document* for *purpose* ('view3d' or
        'pdf') through the portal."""
        self.ensure_one()
        if self._plm_portal_access_level() == "none" or not document:
            return False
        if purpose not in self._plm_portal_document_policy(document):
            return False
        products = document.sudo().linkedcomponents
        return bool(products & self._plm_portal_products())

    plm_access_id = fields.Many2one(
        "plm.access",
        "Default PLM Access",
        help="Where the PLM documents this user creates go, when nothing else "
        "decides it: a new revision stays with the previous ones. Empty means "
        "the root node of the company the user is working in.",
    )

    def getMacros(self):
        """
        Omnia Client Macro module make an overload of this function and enable macros
        """
        return []

    def getCustomProcedure(self):
        """
        Omnia CustomProcedure module make an overload of this function and enable macros
        """
        return "", ""

    @api.model
    def koo_context_get(self):
        return dict(self.context_get())


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
