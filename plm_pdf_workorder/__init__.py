# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
from . import models

def _pre_init_plm_mrp_workorder(env):
    module_obj = env['ir.module.module']

    # Check 'web_enterprise' is installed
    enterprise_module = module_obj.search([('name', '=', 'web_enterprise')], limit=1)

    if enterprise_module and enterprise_module.state == 'installed':
        # Install 'mrp_workorder' module
        mrp_module = module_obj.search([('name', '=', 'mrp_workorder')], limit=1)
        if mrp_module and mrp_module.state != 'installed':
            mrp_module.button_install()

    else:
        # Install 'plm_mrp_workorder' module
        plm_module = module_obj.search([('name', '=', 'plm_mrp_workorder')], limit=1)
        if plm_module and plm_module.state != 'installed':
            plm_module.button_install()
