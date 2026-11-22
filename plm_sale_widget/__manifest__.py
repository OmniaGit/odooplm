##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2026 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
    "name": "PLM Sale Widget",
    "version": "18.0.1.0.0",
    "author": "OmniaSolutions",
    "website": "https://github.com/OmniaGit/odooplm",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "Product image, 3D model and PDF in the sale order lines",
    "description": """
        The product of the sale order line shows its image (zoom on hover)
        and the buttons 3D (the 3D web model of its support files) and PDF
        (the printout of its drawings). The native CAD files are never shown
        nor downloadable from there.
        The widget plm_sale_many2one_image does the same on any product field.
        """,
    "depends": ["plm", "plm_web_3d", "sale"],
    "data": [
        "views/sale_order.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "plm_sale_widget/static/src/js/sale_product_image.js",
            "plm_sale_widget/static/src/xml/sale_product_image.xml",
            "plm_sale_widget/static/src/js/sale_product_field.js",
            "plm_sale_widget/static/src/xml/sale_product_field.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
