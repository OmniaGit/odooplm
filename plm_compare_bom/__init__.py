# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
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
from . import wizard


ORIGINAL_OPEN_BOM_LINES_CODE = """
                action = {
                    'type': 'ir.actions.act_window',
                    'name': 'BoM Lines',
                    'res_model': 'mrp.bom.line',
                    'views': [(env.ref('mrp.mrp_bom_line_view_pivot').id, 'pivot'), (env.ref('mrp.mrp_bom_line_view_list').id, 'list')],
                    'domain': [('bom_id', 'in', env.context.get('active_ids'))],
                }
            """

def uninstall_hook(env):
    """when module install then restore back the odoo core Compare BoMs"""
    action = env.ref("mrp.action_open_bom_lines", raise_if_not_found=False)
    if action and "plm.compare.bom" in (action.code or ""):
        action.code = ORIGINAL_OPEN_BOM_LINES_CODE
