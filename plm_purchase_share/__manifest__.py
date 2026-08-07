# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    "name": "PLM Purchase Share",
    "version": "19.0.1.0.1",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "website": "https://odooplm.omniasolutions.website",
    "support": "https://github.com/OmniaGit/odooplm/issues",
    "live_test_url": "https://v19.odooplm.cloud",
    "sequence": 15,
    "license": "AGPL-3",
    "development_status": "Production/Stable",
    "contributors": [
        "Matteo Boscolo <matteo.boscolo@omniasolutions.eu>",
        "Aadil Belim <aadil.belim@aktivsoftware.com>",
    ],
    "summary": "Supplier document sharing: download the engineering documents of a purchase order from the portal, at the current revision",
    "description": """
        Allow to download documents from the portal.
        """,
    "depends": ["plm", "purchase", "portal", "website"],
    "data": [
        "security/data.xml",
        "views/portal_templates.xml",
    ],
    "images": ["static/description/cover.gif"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
