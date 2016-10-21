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
Created on 31 Aug 2016

@author: Daniel Smerghetto
'''
import odoo.addons.decimal_precision as dp
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
    _inherit = 'product.template'

    engineering_revision = fields.Integer(_('Revision'),
                                          default=0,
                                          required=True,
                                          help=_("The revision of the product."))

    _sql_constraints = [
        ('partnumber_uniq', 'unique (engineering_code,engineering_revision)', _('Part Number has to be unique!'))
    ]

    @api.model
    def init(self):
        cr = self.env.cr
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
