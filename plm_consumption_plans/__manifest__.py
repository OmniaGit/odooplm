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
    "name": "PLM Consumption Plans",
    "version": "18.0.0.0.2",
    "author": "OmniaSolutions",
    "website": "https://odooplm.omniasolutions.website",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "sequence": 15,
    "summary": "Manage and track reference and actual consumption plans for BoM lines",
    "description": """
        PLM Consumption Plans
        This module introduces a structured approach for defining and managing production consumption plans
        within the Product Lifecycle Management (PLM) workflow in Odoo 18
    """,
    "license": "LGPL-3",
    "depends": ["plm"],
    "data": [
        # security files
        "security/ir.model.access.csv",
        # data files
        "data/ir_cron_data.xml",
        # views files
        "views/product_template_views.xml",
        "views/product_product_views.xml",
        "views/plm_template_consumption_plan_menu.xml",
        "views/plm_template_consumption_plan_view.xml",
        "views/mrp_bom_line_views.xml",
        "views/consumption_state_views.xml",
        # report files
        "report/report_consumption_plan.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
