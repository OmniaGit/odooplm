# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<http://www.omniasolutions.eu>).
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
    "name": "PLM Spare",
    "version": "18.0.1.0.1",
    "author": "OmniaSolutions",
    "website": "https://odooplm.omniasolutions.website",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "Add spare BOM and Spare Parts Manual",
    "depends": ["plm"],
    "data": [
        # reporting
        "report/bom_structure.xml",
        "report/product_product.xml",
        # wizards
        "wizards/plm_temporary.xml",
        # views
        "views/plm_description.xml",
        "views/ir_attachment.xml",
        "views/product_product_view.xml",
        "views/mrp_bom_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
