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
Created on 18 Jul 2016

@author: Daniel Smerghetto
'''

import logging
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
                    

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    obsolete_presents = fields.Boolean(_("Obsolete presents"), related='bom_id.obsolete_presents')
