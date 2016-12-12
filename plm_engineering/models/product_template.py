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
Created on 23 Sep 2016

@author: Daniel Smerghetto
'''
from openerp import models
from openerp import fields
from openerp import api
from openerp import _


class ProductTemplateExtension(models.Model):
    _inherit = 'product.template'

    @api.multi
    def engineering_products_open(self):
        product_id = False
        relatedProductBrwsList = self.env['product.product'].search([('product_tmpl_id', '=', self.id)])
        for relatedProductBrws in relatedProductBrwsList:
            product_id = relatedProductBrws.id
        mod_obj = self.env['ir.model.data']
        search_res = mod_obj.get_object_reference('plm', 'plm_component_base_form')
        form_id = search_res and search_res[1] or False
        if product_id and form_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Product Engineering'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.product',
                'res_id': product_id,
                'views': [(form_id, 'form')],
            }

ProductTemplateExtension()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
