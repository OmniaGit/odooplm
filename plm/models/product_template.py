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
import odoo.addons.decimal_precision as dp
from odoo import models
from odoo import fields
from odoo import api
from odoo import _

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
                             default='draft',
                             help=_("The status of the product in its LifeCycle."),
                             readonly="True")
    engineering_material = fields.Char(_('Raw Material'),
                                       size=128,
                                       required=False,
                                       help=_("Raw material for current product, only description for titleblock."))
    engineering_surface = fields.Char(_('Surface Finishing'),
                                      size=128,
                                      required=False,
                                      help=_("Surface finishing for current product, only description for titleblock."))

    engineering_revision = fields.Integer(_('Revision'), required=True, help=_("The revision of the product."), default=0)

    engineering_code = fields.Char(_('Part Number'),
                                   help=_("This is engineering reference to manage a different P/N from item Name."),
                                   size=64)

#   ####################################    Overload to set default values    ####################################
    standard_price = fields.Float('Cost',
                                  compute='_compute_standard_price',
                                  inverse='_set_standard_price',
                                  search='_search_standard_price',
                                  digits=dp.get_precision('Product Price'),
                                  groups="base.group_user",
                                  default=0,
                                  help="Cost of the product, in the default unit of measure of the product.")

    sale_ok = fields.Boolean('Can be Sold',
                             default=False,
                             help="Specify if the product can be selected in a sales order line.")

    engineering_writable = fields.Boolean(_('Writable'),
                                          default=True)

    _sql_constraints = [
        ('partnumber_uniq', 'unique (engineering_code,engineering_revision)', _('Part Number has to be unique!'))
    ]

    @api.model
    def init(self):
        cr = self.env.cr
        cr.execute("""
-- Index: product_template_engcode_index

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
