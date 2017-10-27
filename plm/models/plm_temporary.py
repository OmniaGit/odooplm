# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
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

'''
Created on 12 Dec 2016

@author: Daniel Smerghetto
'''
from odoo import fields
from odoo import osv
from odoo import _


class ProductTemporary(osv.osv.osv_memory):
    _name = "plm.temporary"
    _description = "Temporary Class"
    name = fields.Char(_('Temp'), size=128)
    summarize = fields.Boolean('Summarize Bom Lines if needed.', help="If set as true, when a Bom line comes from EBOM was in the old normal BOM two lines where been summarized.")
    migrate_custom_lines = fields.Boolean(_('Preserve custom BOM lines from previous Normal BOM revision'),
                                          default=True,
                                          help=_("If the user adds custom BOM lines in the revision 0 BOM, than makes the revision 1, creates it's engineering BOM and than create the new Normal BOM form EBOM your revision 0 custom BOM lines are created in the new BOM"))
 
ProductTemporary()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
