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
    "name": "PLM Tools for the Odoo AI Agent",
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
    Answer PLM questions inside Odoo's own chat, with the tools of the MCP server.
    """,
    "description": """
PLM Tools for the Odoo AI Agent
===============================

The MCP server answers PLM questions asked from outside Odoo — an assistant, an
editor, an agent of your own. Odoo Enterprise has an assistant of its own in the
chat, which does not speak MCP: its tools are server actions.

This module gives that assistant the same tools, generated from the same
registry. Nothing is written twice: the names, the descriptions and the
parameter schemas are the ones already declared for MCP, turned into server
actions and gathered in a topic the agent can be given. A tool added tomorrow
appears in both worlds without touching this module.

Requires Odoo Enterprise (the ``ai`` module, which is proprietary) and the
PostgreSQL ``vector`` extension it depends on. Everything else in the suite
works without it: an installation on Community keeps the MCP server and simply
does not install this.
""",
    "depends": [
        "plm_mcp",
        "ai",
    ],
    "data": [
        "data/ai_topic.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
