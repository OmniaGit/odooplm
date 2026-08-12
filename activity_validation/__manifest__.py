# -*- encoding: utf-8 -*-
# ##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2019 OmniaSolutions (<https://www.omniasolutions.website>).
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
    "name": "Activity Validation",
    "version": "19.0.1.0.3",
    "images": ["static/description/cover.gif"],
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "website": "https://odooplm.omniasolutions.website",
    "support": "https://github.com/OmniaGit/odooplm/issues",
    "live_test_url": "https://v19.odooplm.cloud",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 1,
    "summary": "Engineering change requests and orders: modification requests from Odoo and from the CAD application, checked against the bill of material",
    "depends": [
        "mail",
        "plm",
    ],
    "license": "AGPL-3",
    "development_status": "Production/Stable",
    "contributors": [
        "Matteo Boscolo <matteo.boscolo@omniasolutions.eu>",
        "Daniel Smerghetto <daniel.smerghetto@omniasolutions.eu>",
        "Jayraj Thakkar <jayraj.thakkar@omniasolutions.eu>",
        "Kuldip Trapasiya <kuldip.trapasiya@aktivsoftware.com>",
        "Aadil Belim <aadil.belim@aktivsoftware.com>",
        "Michele Vallese <mvallese@omniasolutions.eu>",
        "Maxime Chambreuil <mchambreuil@opensourceintegrators.com>",
        "Leonardo Cazziolati <leonardo.cazziolati@omniasolutions.eu>",
    ],
    "data": [
        "security/security.xml",
        "data/mail_activity_data.xml",
        "views/mail_activity_type.xml",
        "views/mail_activity.xml",
        "views/mail_activity_children_rel.xml",
        "report/bom_activity_product_product.xml",
        "report/bom_activity_product_template.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
