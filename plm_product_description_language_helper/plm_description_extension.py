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
Created on 15 Jun 2016

@author: Daniel Smerghetto
'''
from openerp import models
from openerp import fields
from openerp import _


class PlmDescriptionExtension(models.Model):
    _name = 'plm.description'
    _inherit = 'plm.description'
    name = fields.Char(_('Note to Description'), size=128, translate=True)
    description = fields.Char(_('Standard Description'), size=128, translate=True)
    umc1 = fields.Char(_('UM / Feature 1'), size=32, help=_("Allow to specify a unit measure or a label for the feature."), translate=True)
    umc2 = fields.Char(_('UM / Feature 2'), size=32, help=_("Allow to specify a unit measure or a label for the feature."), translate=True)
    umc3 = fields.Char(_('UM / Feature 3'), size=32, help=_("Allow to specify a unit measure or a label for the feature."), translate=True)

PlmDescriptionExtension()
