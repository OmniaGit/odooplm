##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "PLM Purchase Share",
    "version": "18.0.1.0.0",
    "author": "OmniaSolutions",
    "website": "https://github.com/OmniaGit/odooplm",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "download the products document from the purchase orders on the portal.",
    "description": """
        Allow to download documents from the portal.
        """,
    "depends": ["plm", "purchase", "portal"],
    "data": [
        # security
        "security/data.xml",
        # views
        "views/portal_templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
