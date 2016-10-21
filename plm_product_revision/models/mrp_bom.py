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
from openerp import models
from openerp import fields
from openerp import api
from openerp import _


class MrpBomExtension(models.Model):
    _inherit = 'mrp.bom'

    engineering_revision = fields.Integer(related="product_tmpl_id.engineering_revision",
                                          string=_("Revision"),
                                          help=_("The revision of the product."),
                                          store=False)

    @api.multi
    def copy(self, defaults={}):
        """
            Return new object copied (removing SourceID)
        """
        newBomBrws = super(MrpBomExtension, self).copy(defaults)
        if newBomBrws:
            for bom_line in newBomBrws.bom_line_ids:
                lateRevIdC = self.env['product.product'].GetLatestIds([(bom_line.product_id.product_tmpl_id.engineering_code,
                                                                        False,
                                                                        False)])  # Get Latest revision of each Part
                self.env['mrp.bom.line'].browse([bom_line.id]).write({'source_id': False,
                                                                      'name': bom_line.product_id.product_tmpl_id.name,
                                                                      'product_id': lateRevIdC[0]})
            newBomBrws.write({'source_id': False,
                              'name': newBomBrws.product_tmpl_id.name},
                             check=False)
        return newBomBrws

MrpBomExtension()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
