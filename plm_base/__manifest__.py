##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2022-2022 OmniaSolutions (<https://www.omniasolutions.website>).
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
    "name": "Product Lifecycle Management",
    "version": "16.0.1",
    "author": "OmniaSolutions",
    "website": "https://github.com/OmniaGit/odooplm",
    "category": "Manufacturing/Product Lifecycle Management",
    "sequence": 15,
    "license": "LGPL-3",
    "summary": "PLM-PDM Integration base module [tehcnical module",
    "images": ["static/img/odoo_plm.png"],
    "depends": ["base"],
    "data": [
        # security
        # views
        # QwebTemplates
        # Reports Template
        # Report
    ],
    "assets": {
        "web.assets_backend": [
            ],
        'web.report_assets_common': [
        ],
        },
    "qweb": [],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
    "auto_install": False,
}
