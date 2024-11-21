# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
"""
Created on 8 Oct 2021
@author: mboscolo
"""
from odoo import api, models


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    @api.onchange("state")
    def onchange_line_state(self):
        """
        Force update flag every time bom line state changes
        """
        for bomLineObj in self:
            bomBrws = bomLineObj.bom_id
            bomBrws._obsolete_compute()
