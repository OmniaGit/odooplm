# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solution
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': '[OMNIASOLUTIONS] Production Bom Update',
 'version': '15.2',
 'sequence': 1,
 'category': 'Manufacturing',
 'description': """
============================================================================================================================
This module allows you to update your working manufacture order based on the bom present in the order Taking care of the product revisions.
============================================================================================================================
""",
 'author': 'mboscolo',
 'maintainer': 'https://www.OmniaSolutions.website',
 'website': 'https://odooplm.omniasolutions.website',
 'depends': ['omnia_mrp_bom_update',
             'plm',
             'stock'],
 'data': ['views/mrp_bom_extension.xml'],
 'license': 'AGPL-3',
 'installable': True,
 'application': False,
 'auto_install': False,
}