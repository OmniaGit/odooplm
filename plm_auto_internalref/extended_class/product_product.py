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
Created on 9 Dec 2016

@author: Daniel Smerghetto
'''

from odoo import models
from odoo import api
import logging


class ProductProductExtension(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        engineering_code = vals.get('engineering_code', '')
        engineering_revision = vals.get('engineering_revision', 0)
        if (engineering_code and not vals.get('default_code')) or (engineering_code and engineering_revision > 0):
            vals['default_code'] = '%s_%s' % (engineering_code, engineering_revision)
            logging.info('Internal ref set value %s on engineering_code: %r' % (vals['default_code'], engineering_code))
        return super(ProductProductExtension, self).create(vals)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
