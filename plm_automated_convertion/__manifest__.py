# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2022 OmniaSolutions (<https://www.omniasolutions.website>).
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
    "name": "Product Lifecycle Management Batch conversion",
    "version": "15.0.5",
    "author": "OmniaSolutions",
    "website": "https://github.com/OmniaGit/odooplm",
    "category": "Product Lifecycle Management",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "CAD editors batch conversion tool",
    "depends": ["plm"],
    'external_dependencies': {'python': ['ezdxf',
                                         'matplotlib',
                                         'cadquery',
                                         'numpy-stl']},
    "data": [  
        #
        # security
        #
        'security/security.xml',
        #
        # views
        #
        'view/ir_action_server.xml',
        'view/ir_attachment.xml',
        'view/ir_cron.xml',
        'view/plm_convert_rule.xml',
        'view/plm_convert_servers.xml',
        'view/plm_convert_stack.xml',
        'wizards/plm_convert.xml',
        #
        # data
        #
        'data/data.xml',
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
