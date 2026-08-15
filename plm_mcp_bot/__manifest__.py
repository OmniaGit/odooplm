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
    "name": "PLM Commands for OdooBot",
    "version": "19.0.1.0.0",
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "website": "https://odooplm.omniasolutions.website",
    "support": "https://github.com/OmniaGit/odooplm/issues",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "license": "AGPL-3",
    "summary": """
    Ask the PLM tools by typing /plm in a chat with OdooBot.
    """,
    "description": """
PLM Commands for OdooBot
========================

The tools of the MCP server, reachable by typing. Useful when Odoo is already
open and there is no MCP client at hand — and it costs nothing per question,
because no language model is involved.

    /plm                     the commands
    /plm bom BASE-100        the bill of material
    /plm parte CLP-020-001   the title block and documents
    /plm dove CLP-020-001    where it is used, by revision
    /plm impatto CLP-020-001 what modifying it would touch
    /plm mancanti BASE-100   the components with no drawing
    /plm aperti              what is under modification, and by whom

Same registry as the MCP endpoint, so a tool added there is one command away
from being reachable here too, and the answer obeys the record rules of
whoever typed it.

Not a small agent: the command names the tool, so questions that need two of
them combined — "which components are steel" — still belong to a model. Works
in a chat with OdooBot or when it is mentioned, not in the chatter of a record.
""",
    "depends": [
        "plm_mcp",
        "mail_bot",
    ],
    "data": [],
    "installable": True,
    "application": False,
}
