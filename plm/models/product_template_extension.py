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
Created on 25 Aug 2016

@author: Daniel Smerghetto
'''
from openerp import models
from openerp import fields
from openerp import api
from openerp import _

USED_STATES = [('draft', _('Draft')),
               ('confirmed', _('Confirmed')),
               ('released', _('Released')),
               ('undermodify', _('UnderModify')),
               ('obsoleted', _('Obsoleted'))]


class ProductTemplateExtension(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    state = fields.Selection(USED_STATES,
                             _('Status'),
                             help=_("The status of the product in its LifeCycle."),
                             readonly="True")
    engineering_code = fields.Char(_('Part Number'),
                                   help=_("This is engineering reference to manage a different P/N from item Name."),
                                   size=64)
    engineering_revision = fields.Integer(_('Revision'),
                                          required=True,
                                          help=_("The revision of the product."))
    engineering_writable = fields.Boolean(_('Writable'))
    engineering_material = fields.Char(_('Raw Material'),
                                       size=128,
                                       required=False,
                                       help=_("Raw material for current product, only description for titleblock."))
    engineering_surface = fields.Char(_('Surface Finishing'),
                                      size=128,
                                      required=False,
                                      help=_("Surface finishing for current product, only description for titleblock."))

#   Internal methods
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

    _defaults = {'state': lambda *a: 'draft',
                 'engineering_revision': 0,
                 'engineering_writable': True,
                 'type': 'product',
                 'standard_price': 0,
                 'volume': 0,
                 'weight': 0,
                 'cost_method': 0,
                 'sale_ok': 0,
                 'state': 'draft',
                 'mes_type': 'fixed',
                 'cost_method': 'standard',
                 }
    _sql_constraints = [
        ('partnumber_uniq', 'unique (engineering_code,engineering_revision)', _('Part Number has to be unique!'))
    ]

    def init(self, cr):
        cr.execute("""
-- Index: product_template_engcode_index

DROP INDEX IF EXISTS product_template_engcode_index;

CREATE INDEX product_template_engcode_index
  ON product_template
  USING btree
  (engineering_code);
  """)

        cr.execute("""
-- Index: product_template_engcoderev_index

DROP INDEX IF EXISTS product_template_engcoderev_index;

CREATE INDEX product_template_engcoderev_index
  ON product_template
  USING btree
  (engineering_code, engineering_revision);
  """)

ProductTemplateExtension()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
