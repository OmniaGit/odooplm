# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<http://www.omniasolutions.eu>).
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
    "name": "PLM Suspended State",
    "version": "19.0.1.0.2",
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
        "Jose Luis S. A. <alagunasalahaddin@live.com>",
        "Jayraj Thakkar <jayraj.thakkar@omniasolutions.eu>",
        "Michele Vallese <mvallese@omniasolutions.eu>",
        "Daniel Smerghetto <daniel.smerghetto@omniasolutions.eu>",
        "Kuldip Trapasiya <kuldip.trapasiya@aktivsoftware.com>",
        "OmniaSolutions <omniagit@omniasolutions.eu>",
        "Maxime Chambreuil <mchambreuil@opensourceintegrators.com>",
        "Leonardo Cazziolati <leonardo.cazziolati@omniasolutions.eu>",
    ],
    "summary": "Add a suspended state to the engineering workflow, for products and documents",
    "depends": ["mrp", "plm"],
    "data": [
        # views
        "views/ir_attachment.xml",
        "views/product_product.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
