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
Created on 30 Aug 2016

@author: Daniel Smerghetto
'''

from openerp import models
from openerp import fields
from openerp import api
from openerp import _


class MrpBomLineExtension(models.Model):
    _inherit = 'mrp.bom.line'

    @api.model
    def _get_reference_spare_type(self):
        return self.env['mrp.bom']._get_reference_spare_type()

    type = fields.Selection('_get_reference_spare_type',
                            _('BoM Type'),
                            required=True,
                            default='normal',
                            help=_("Phantom BOM: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product."
                                   " Ship this product as a set of components (kit)."))

MrpBomLineExtension()
