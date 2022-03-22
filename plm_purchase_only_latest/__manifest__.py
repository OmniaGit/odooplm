##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
    'name': 'PLM Purchase Only Latest',
    'version': '15.0.2',
    'author': 'OmniaSolutions',
    'website': 'https://www.omniasolutions.website',
    'category': 'Product Lifecycle Management',
    'sequence': 15,
    'license': 'AGPL-3',
    'summary': 'Show only latest product version in purchase',
    'images': ['static/img/odoo_plm.png'],
    'depends': ['plm', 'purchase'],
    'description': """
    Allow to select only product that have not have engineering_code or is in the latest revision for Purchase
    """,
    'data': [
            'views/purchase_order_line.xml'
            ],
    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
