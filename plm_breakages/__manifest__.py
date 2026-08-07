# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2020-2021 OmniaSolutions (<https://omniasolutions.website>).
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
# Leonardo Cazziolati
# leonardo.cazziolati@omniasolutions.eu
# 23-06-2020

{
    "name": "PLM Breakages",
    "version": "19.0.1.0.0",
    "images": ["static/description/cover.gif"],
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "website": "https://odooplm.omniasolutions.website",
    "support": "https://github.com/OmniaGit/odooplm/issues",
    "live_test_url": "https://v19.odooplm.cloud",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "license": "AGPL-3",
    "development_status": "Production/Stable",
    "contributors": [
        "Matteo Boscolo <matteo.boscolo@omniasolutions.eu>",
        "Michele Vallese <mvallese@omniasolutions.eu>",
        "Kuldip Trapasiya <kuldip.trapasiya@aktivsoftware.com>",
        "Leonardo Cazziolati <leonardo.cazziolati@omniasolutions.eu>",
        "Jayraj Thakkar <jayraj.thakkar@omniasolutions.eu>",
        "Maxime Chambreuil <mchambreuil@opensourceintegrators.com>",
    ],
    "summary": "PLM Breakages",
    "depends": ["base", "product", "mrp","plm"],
    "data": [
        "security/base_plm_security.xml",
        "data/sequence.xml",
        "views/breakages_view.xml",
        "views/product_view.xml",
        "views/bom_view.xml",
        "views/mrp_production.xml",
    ],
    "installable": True,
}
