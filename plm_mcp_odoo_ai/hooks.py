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
"""Publish the tools when the module is installed, and on every update.

Generated rather than declared in a data file: the tools live in the code of
whichever modules are installed, so the only way for the list to stay right is
to read it at install time. Running it again is safe — the actions are matched
by external id and rewritten in place.
"""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    _logger.info("plm_mcp_odoo_ai: publishing the PLM tools to the Odoo agent")
    env["plm.mcp.tool"]._sync_odoo_ai_tools()
