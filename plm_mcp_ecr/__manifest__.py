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
{
    "name": "PLM MCP Server — Change Requests",
    "version": "19.0.1.0.0",
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "website": "https://odooplm.omniasolutions.website",
    "support": "https://github.com/OmniaGit/odooplm/issues",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 20,
    "license": "AGPL-3",
    "development_status": "Alpha",
    "contributors": [
        "Matteo Boscolo <matteo.boscolo@omniasolutions.eu>",
    ],
    "summary": """
    Ask the MCP server about engineering change requests and change orders.
    """,
    "description": """
PLM MCP Server — Change Requests
================================

Adds the change request and change order questions to the MCP server: what is
open, what is waiting for whom, and what the person asking has to validate.

It is a module of its own rather than part of ``plm_mcp`` because change
requests come from ``activity_validation``, and a PLM server should answer
questions about parts and drawings whether or not that module is installed.
Installing this one adds the tools; removing it takes them away, and nothing
else changes.

That it can be done this way is the point of how the tools are declared: a tool
is a method on the ``plm.mcp.tool`` abstract model, so any module that inherits
it and decorates a method has a working tool, with no registration step and no
data file to keep in step with the code.
""",
    "depends": [
        "plm_mcp",
        "activity_validation",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
