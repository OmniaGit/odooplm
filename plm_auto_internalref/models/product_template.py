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

    def legacy_update_IR(self):
        #
        # Use this function in order to update all your db lagacy data 
        #
        pt_ids=self.search([])
        total_updatable = len(pt_ids)
        updated=0
        not_updated=0
        for index, pt in enumerate(pt_ids):
            ctx_pp = self.env['product.product'].with_context(new_revision=True)
            pt_new_default_code = ctx_pp.computeDefaultCode({}, pt)
            pp_new_default_code = ctx_pp.computeDefaultCode({}, pt.product_variant_id)
            new_default_code = pt_new_default_code or pp_new_default_code
            if new_default_code:
                pt.default_code = new_default_code
                pt.product_variant_id.default_code=new_default_code
                updated+=1
            else:
                not_updated+=1
            logging.info("%s/%s Updated %s not Updated %s Update product %s" % (index,
                                                                                total_updatable,
                                                                                updated,
                                                                                not_updated,
                                                                                pt.display_name))    
        logging.info("Updated product %s not updated %s" % (updated, not_updated))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: