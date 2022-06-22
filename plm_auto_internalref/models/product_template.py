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
Created on 9 Dec 2016

@author: Daniel Smerghetto
'''

from odoo import models
from odoo import api
import logging


class ProductTemplateExtension(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    @api.model
    def create(self, vals):
        new_default_code = self.env['product.product'].computeDefaultCode(vals)
        if new_default_code:
            logging.info('OdooPLM: Default Code set to %s ' % (new_default_code))
            vals['default_code'] = new_default_code
        return super(ProductTemplateExtension, self).create(vals)

    def write(self, vals):
        new_default_code = self.env['product.product'].computeDefaultCode(vals,
                                                                          self)
        if new_default_code :
            logging.info('OdooPLM: Default Code set to %s ' % (new_default_code))
            vals['default_code'] = new_default_code
        return super(ProductTemplateExtension, self).write(vals)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
