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
Created on 25 Aug 2016

@author: Daniel Smerghetto
'''
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        ret = super(ProductProduct, self).name_search(name=name, args=args, operator=operator, limit=limit)
        out = []
        if self.env.context.get('produce_latest'):
            for prod_id, val in ret:
                eng_code = self.browse(prod_id).engineering_code
                latest_product = self.search([('engineering_code', '=', eng_code)], order='engineering_revision desc', limit=1)
                if prod_id == latest_product.id:
                    out.append((prod_id, val))
        return out or ret
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: