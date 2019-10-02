# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2019 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
    'name': 'Product Lifecycle Management Batch conversion',
    'version': '13.0',
    'author': 'OmniaSolutions',
    'website': 'https://www.omniasolutions.website',
    'category': 'Product Lifecycle Management',
    'sequence': 15,
    'license': 'AGPL-3',
    'summary': 'PLM Integration with main CAD editors batch conversion tool',
    'depends': ['plm'],
    'description': """
Manage Product Lifecycle Management in OpenERP
==============================================
Batch conversion tool
Improve the plm module adding feature for converting cad files in different formats using a cad server machine
in order to properly set this module you need a cad server machine.
for more information send an e mail at info@omniasolutions.eu
    """,
    'data': ['view/plm_component_action_extended.xml',
             'view/data.xml'],
    'demo': [],
    'test': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
