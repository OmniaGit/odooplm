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
Created on 19 Jul 2016

@author: Daniel Smerghetto
'''
from openerp.osv import osv
from openerp.report import report_sxw
from openerp import _
import time
from openerp.addons.plm.report.bom_structure import bom_structure_all_custom_report


class report_plm_bom_obsoleted(osv.AbstractModel):
    _name = 'report.plm_date_bom.plm_bom_obsoleted'
    _inherit = 'report.abstract_report'
    _template = 'plm_date_bom.plm_bom_obsoleted'
    _wrapped_report_class = bom_structure_all_custom_report
