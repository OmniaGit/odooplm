# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<http://www.omniasolutions.eu>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, Trueeither version 3 of the License, or
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
# Developed: matteo.boscolo@omniasolutions.eu (2017)
##############################################################################
{
    "name": "PLM Project",
    "version": "19.0.1.0.1",
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
        "Jayraj Thakkar <jayraj.thakkar@omniasolutions.eu>",
        "Daniel Smerghetto <daniel.smerghetto@omniasolutions.eu>",
        "Kuldip Trapasiya <kuldip.trapasiya@aktivsoftware.com>",
        "Michele Vallese <mvallese@omniasolutions.eu>",
        "Jose Luis S. A. <alagunasalahaddin@live.com>",
        "Maxime Chambreuil <mchambreuil@opensourceintegrators.com>",
    ],
    "sequence": 15,
    "summary": "Connect odoo project with odooPLM",
    "depends": ["plm", "project"],
    "data": [
        "views/project.xml",
        "views/product.xml",
        "views/project_task.xml",
        "views/mail_activity_type.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
