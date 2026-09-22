# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from odoo import fields, models

# The labels are plain strings on purpose: Odoo exports the labels of a
# selection to the catalogues on its own (model:ir.model.fields.selection),
# while _() here would run at import time and freeze one language.
PORTAL_ACCESS_LEVELS = [
    ("none", "No PLM documents"),
    ("view", "View only"),
    ("markup", "View and markup"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    plm_portal_access = fields.Selection(
        PORTAL_ACCESS_LEVELS,
        string="PLM Portal Access",
        default="none",
        help="What the portal users of this partner may do with the PLM "
        "documents of what they bought or sold: nothing, look at them, or also "
        "annotate them in the 3D viewer. It is set on the company of the "
        "contact; a single user can be given another level on their own form.",
    )
    plm_portal_spares = fields.Boolean(
        "PLM Portal Spare Parts",
        help="A customer with this set walks the spare parts of what they "
        "bought: the components of its spare bill of materials, and of theirs, "
        "down to the last level. Without it they see the products of their "
        "order lines only.",
    )
