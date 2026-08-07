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
    "name": "PLM Purchase Only Latest",
    "version": "19.0.1.0.0",
    "images": ["static/description/cover.gif"],
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "website": "https://odooplm.omniasolutions.website",
    "support": "https://github.com/OmniaGit/odooplm/issues",
    "live_test_url": "https://v19.odooplm.cloud",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "development_status": "Production/Stable",
    "contributors": [
        "Matteo Boscolo <matteo.boscolo@omniasolutions.eu>",
        "Jayraj Thakkar <jayraj.thakkar@omniasolutions.eu>",
        "Michele Vallese <mvallese@omniasolutions.eu>",
        "Kuldip Trapasiya <kuldip.trapasiya@aktivsoftware.com>",
    ],
    "summary": "Show only latest product version in purchase",
    "description": """
        Allow to select only product that have not have engineering_code
        or is in the latest revision for Purchase
        """,
    "depends": ["plm", "purchase"],
    "data": ["data/purchase_only_parameter.xml", "views/purchase_views.xml"],
    "installable": True,
    "application": False,
    "auto_install": False,
}

