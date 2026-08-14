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
    "name": "PLM MCP Server",
    "version": "19.0.1.0.0",
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "website": "https://odooplm.omniasolutions.website",
    "support": "https://github.com/OmniaGit/odooplm/issues",
    "live_test_url": "https://v19.odooplm.cloud",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 20,
    "license": "AGPL-3",
    "development_status": "Alpha",
    "contributors": [
        "Matteo Boscolo <matteo.boscolo@omniasolutions.eu>",
    ],
    "summary": """
    Answer questions about the engineering data over the Model Context Protocol.
    """,
    "description": """
PLM MCP Server
==============

Exposes OdooPLM as an MCP server, so an AI assistant — any client that speaks
the protocol — can be asked questions about the engineering data and answer them
from the live database instead of guessing: where a part is used, what changed
between two revisions, which parts are under modification, which documents are
checked out.

The endpoint speaks the protocol over plain HTTP from an Odoo controller: there
is no separate process to deploy and no asyncio in the stack. The wire types
come from ``mcp-types``, the package published by the protocol's own authors, so
the message shapes stay correct as the specification moves.

Access is through API keys, and a key is not an identity of its own: it points
at an Odoo user, and every call runs with that user's rights. Whatever the PLM
record rules hide from the person stays hidden from the agent.

Every tool is read-only. Nothing here releases a part, creates a revision or
checks out a document — an agent that gets a question wrong costs thirty
seconds, one that gets a state change wrong costs a lot more.
""",
    "depends": [
        "plm",
    ],
    "external_dependencies": {
        "python": ["mcp-types"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/plm_mcp_key_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
