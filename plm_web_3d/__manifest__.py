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
    "name": "PLM Web 3d Support",
    "version": "18.0.3.0.14",
    "author": "OmniaSolutions",
    "website": "https://github.com/OmniaGit/odooplm",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": """
    This Module allows you to view 3D mode file and 2D documents in odoo.
    it allows to:
    * 3d viewer
    * 3d model viewer
    * cad viewer
    * 2d viewer
    * 2d drawing viewer
    Made using:
    * webgl
    * treejs
    """,
    "images": ["static/src/img/web_3d.gif"],
    "depends": ["plm"],
    "data": [
        "security/ir.model.access.csv",
        "views/ir_attachment.xml",
        "views/web_template.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
