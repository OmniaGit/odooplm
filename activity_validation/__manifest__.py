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
    'name': 'Activity Validation',
    'version': '13.2',
    'author': 'OmniaSolutions',
    'website': 'https://www.omniasolutions.website',
    'category': 'Custom',
    'sequence': 1,
    'summary': '',
    'depends': [
        'base',
        'product',
        'mail',
    ],
    'license': 'AGPL-3',
    'description': '',
    'data': [
        #'security/ir.model.access.csv',
        'data/mail_activity_data.xml',
        'views/mail_activity_type.xml',
        'views/mail_activity.xml',
        'views/mail_activity_children_rel.xml',
        'static/src/xml/import_js.xml',
        'security/security.xml',
    ],
    'demo': [],
    'test': [],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
