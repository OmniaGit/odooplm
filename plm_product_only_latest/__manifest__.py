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
    'name': 'PLM Produce Only Latest',
    'version': '12.0.2',
    'author': 'OmniaSolutions',
    'website': 'https://www.omniasolutions.website',
    'category': 'Product Lifecycle Management',
    'sequence': 15,
    'license': 'AGPL-3',
    'summary': 'PLM Integration with main CAD editors',
    'images': ['static/img/odoo_plm.png'],
    'depends': ['plm', 'sale'],
    'description': """
    Allow to select only components in the latest revision for purchase
    """,
    'data': [
            'views/mrp_production.xml'
            ],
    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
