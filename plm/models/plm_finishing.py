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

"""
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class PlmFinishing(models.Model):
    _name = "plm.finishing"
    _description = "Surface Finishing"

    name = fields.Char(_('Specification'),
                       required=True,
                       translate=True)
    description = fields.Char(_('Description'),
                              size=128)
    sequence = fields.Integer(_('Sequence'),
                              help=_("Gives the sequence order when displaying a list of product categories."))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', _('Surface Finishing has to be unique !')),
    ]

    def copy(self, default=None):
        if not default:
            default = {}
        default['name'] = self.name + ' (copy)'
        return super(PlmFinishing, self).copy(default=default)
