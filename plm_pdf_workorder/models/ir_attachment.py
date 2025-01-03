# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2020 https://OmniaSolutions.website
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
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    is_production_doc = fields.Boolean("Production Document")
    doc_seq = fields.Char("Doc Sequence", readonly=True, compute="_compute_doc_seq")

    def _compute_doc_seq(self):
        for attachment in self:
            products = self.env["product.product"].search(
                [("linkeddocuments", "in", attachment.id)]
            )
            if products:
                product = products[0]
                linked_attachments = product.linkeddocuments.sorted("create_date")
                attachment.doc_seq = linked_attachments.ids.index(attachment.id) + 1
            else:
                attachment.doc_seq = 0
