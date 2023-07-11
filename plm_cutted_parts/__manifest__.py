##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<https://www.omniasolutions.website>).
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
#######################True#######################################################
{
    "name": "PLM Cutted Parts",
    "version": "16.0.4",
    "author": "OmniaSolutions",
    "website": "https://odooplm.omniasolutions.website",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "summary": "Manage bom explosion for cutted parts",
    "images": [],
    "license": "AGPL-3",
    "depends": ["mrp",
                "plm"],
    "data": [
        "views/product.xml",
        "views/mrp_bom_lines.xml",
        "report/mrp_bom.xml",
        "security/base_plm_security.xml",
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
