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
        engineering_code = vals.get('engineering_code', '')
        engineering_revision = vals.get('engineering_revision', 0)
        if 'engineering_code' in vals:
            if engineering_code and engineering_code != '-' and self.env.context.get('odooPLM') or self.env.context.get('new_revision', False):  # Cloning by client
                vals['default_code'] = self.computeDefaultCode(engineering_code, engineering_revision)
                logging.info('Internal ref set value %s on engineering_code: %r' % (vals['default_code'], engineering_code))
            elif engineering_code and not vals.get('default_code') and engineering_code != '-':
                vals['default_code'] = self.computeDefaultCode(engineering_code, engineering_revision)
                logging.info('Internal ref set value %s on engineering_code: %r' % (vals['default_code'], engineering_code))
        return super(ProductProductExtension, self).create(vals)

    def computeDefaultCode(self, eng_code, eng_rev):
        return '%s_%s' % (eng_code, eng_rev)

    def write(self, vals):
        res = super(ProductProductExtension, self).write(vals)
        if 'engineering_code' in vals:
            for prodBrws in self:
                if prodBrws.engineering_code and prodBrws.engineering_code != '-' and self.env.context.get('odooPLM'):  # Cloning by client
                    default_code = self.computeDefaultCode(prodBrws.engineering_code, prodBrws.engineering_revision)
                    super(ProductProductExtension, self).write({'default_code': default_code})
                elif prodBrws.engineering_code and not prodBrws.default_code and prodBrws.engineering_code != '-':
                    default_code = self.computeDefaultCode(prodBrws.engineering_code, prodBrws.engineering_revision)
                    super(ProductProductExtension, self).write({'default_code': default_code})
        return res
