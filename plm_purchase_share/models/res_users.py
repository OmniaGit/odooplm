# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from odoo import models

from odoo.addons.plm.models.plm_mixin import (
    OBSOLATED_STATUS,
    RELEASED_STATUSES,
)

# A drawing reaches a vendor once it has been released; it stays theirs when a
# later revision obsoletes it, since the line pins the revision they bought.
PORTAL_PRINTOUT_STATES = RELEASED_STATUSES + [OBSOLATED_STATUS]


class ResUsers(models.Model):
    _inherit = "res.users"

    def _plm_portal_printouts(self, product, scope=None):
        """The drawings of *product* this user may download as PDF from the
        portal: the product has to be in their scope (res.users.
        _plm_portal_products) and the format policy has to allow the PDF of the
        document (_plm_portal_document_policy). The result is a sudo
        recordset, since the portal cannot read attachments.

        *scope* is the user's _plm_portal_products(), when the caller already
        has it: a page listing many order lines asks once.
        """
        self.ensure_one()
        documents = self.env["ir.attachment"].sudo().browse()
        product = product.sudo()
        if not product:
            return documents
        if scope is None:
            scope = self._plm_portal_products()
        if product not in scope:
            return documents
        return product.linkeddocuments.filtered(
            lambda document: document.engineering_state in PORTAL_PRINTOUT_STATES
            and "pdf" in self._plm_portal_document_policy(document)
        )
