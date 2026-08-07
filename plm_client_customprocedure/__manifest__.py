# -*- encoding: utf-8 -*-
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
##############################################################################
{
    "name": "PLM Client Custom Procedure",
    "version": "19.0.1.0.1",
    "images": ["static/description/cover.gif"],
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "website": "https://odooplm.omniasolutions.website",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "summary": "PLM Client Custom Procedure",
    "license": "AGPL-3",
    "depends": [
        "plm",
        "plm_automated_convertion"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/res_users.xml",
        "views/res_groups.xml",
        "views/ir_attachment_views.xml",
        "views/cad_config_views.xml",
        "views/property_update_wizard.xml",
        "views/odoo_cad_mapping_views.xml",
        "views/plm_convert_stack.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
