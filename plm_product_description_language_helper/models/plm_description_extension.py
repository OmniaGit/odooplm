# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
Created on 15 Jun 2016

@author: Daniel Smerghetto
'''
from odoo import models
from odoo import fields
from odoo import _


class PlmDescriptionExtension(models.Model):
    _name = 'plm.description'
    _inherit = 'plm.description'
    
    name = fields.Char('Note to Description',
                       translate=True)
    description = fields.Char('Standard Description',
                              translate=True)
    umc1 = fields.Char('UM / Feature 1',
                       translate=True,
                       help=_("Allow to specify a unit measure or a label for the feature."))
    umc2 = fields.Char('UM / Feature 2',
                       translate=True,
                       help=_("Allow to specify a unit measure or a label for the feature."))
    umc3 = fields.Char('UM / Feature 3',
                       translate=True,
                       help=_("Allow to specify a unit measure or a label for the feature."))

