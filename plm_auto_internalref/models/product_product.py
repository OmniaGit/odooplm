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
Created on 9 Dec 2016

@author: Daniel Smerghetto
"""

import logging
from odoo import models
from odoo import api


class ProductProductExtension(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        new_default_code = self.computeDefaultCode(vals)
        if new_default_code:
            logging.info('OdooPLM: Default Code set to %s ' % (new_default_code))
            vals['default_code'] = new_default_code
        return super(ProductProductExtension, self).create(vals)
    
    @property
    def getDefaultCodeTemplate(self):
        #
        # overwritable function to customize internal reference
        #
        return "%s_%s"
    
    def computeDefaultCode(self,
                           vals={},
                           objBrowse=None):
        """
        Function to be overloaded for changing the inetrnal referense computation
        :vals dict like with all the value that be updated
        :objBrowse product.product or product.template in case of write operation
        """
        out = False
        in_revision = self.env.context.get('new_revision', False)
        engineering_code = vals.get('engineering_code', '')
        engineering_revision = vals.get('engineering_revision', 0)
        default_code = vals.get('default_code')
        if objBrowse: #suppose write operation
            if not engineering_code:
                engineering_code = objBrowse.engineering_code
            if not engineering_revision:
                engineering_revision = objBrowse.engineering_revision
            if not default_code:
                default_code = objBrowse.default_code            
        if in_revision and engineering_code and engineering_code != '-':
            out = self.getDefaultCodeTemplate % (engineering_code, engineering_revision)
        if engineering_code and not default_code and engineering_code != '-':
            out = self.getDefaultCodeTemplate % (engineering_code, engineering_revision)
        if default_code == out:
            return False
        return out

    def write(self, vals):
        for product_id in self:
            new_default_code = self.computeDefaultCode(vals,
                                                       product_id)
            if new_default_code :
                logging.info('OdooPLM: Default Code set to %s ' % (new_default_code))
                vals['default_code'] = new_default_code
            break
        return super(ProductProductExtension, self).write(vals)
