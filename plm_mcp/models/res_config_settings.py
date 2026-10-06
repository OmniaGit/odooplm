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
"""The two switches of the OAuth flow, on the PLM settings page."""
from odoo import fields, models

from .plm_mcp_oauth_client import PARAM_CIMD, PARAM_DCR


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    plm_mcp_oauth_cimd_urls = fields.Char(
        string="Applications allowed to connect",
        config_parameter=PARAM_CIMD,
        groups="plm.group_plm_admin",
        help="One metadata address per line. An AI application that names "
             "itself by one of these can ask a person for access.",
    )
    plm_mcp_oauth_enable_dcr = fields.Boolean(
        string="Let applications register themselves",
        config_parameter=PARAM_DCR,
        groups="plm.group_plm_admin",
        help="Any application can then ask to be known, and a person still has "
             "to log in and allow it. Leave off unless a client cannot use a "
             "metadata address.",
    )
