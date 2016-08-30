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


class MrpBomLineExtension(models.Model):
    _name = 'mrp.bom.line'
    _inherit = 'mrp.bom.line'
    _order = "itemnum"

    @api.one
    def _get_child_bom_lines(self):
        """
            If the BOM line refers to a BOM, return the ids of the child BOM lines
        """
        bom_obj = self.env['mrp.bom']
        for bom_line in self:
            for bom_id in self.search([('product_id', '=', bom_line.product_id.id),
                                      ('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                                      ('type', '=', bom_line.type)]):
                child_bom = bom_obj.browse(bom_id)
                for childBomLine in child_bom.bom_line_ids:
                    childBomLine._get_child_bom_lines()
                self.child_line_ids = [x.id for x in child_bom.bom_line_ids]
                return
            else:
                self.child_line_ids = False

    state = fields.Selection(related="product_id.state",
                             string=_("Status"),
                             help=_("The status of the product in its LifeCycle."),
                             store=False)
    engineering_revision = fields.Integer(related="product_id.engineering_revision",
                                          string=_("Revision"),
                                          help=_("The revision of the product."),
                                          store=False)
    description = fields.Text(related="product_id.description",
                              string=_("Description"),
                              store=False)
    weight_net = fields.Float(related="product_id.weight",
                              string=_("Weight Net"),
                              store=False)
    create_date = fields.Datetime(_('Creation Date'),
                                  readonly=True)
    source_id = fields.Many2one('plm.document',
                                'name',
                                ondelete='no action',
                                readonly=True,
                                help=_("This is the document object that declares this BoM."))
    type = fields.Selection([('normal', _('Normal BoM')),
                             ('phantom', _('Sets / Phantom')),
                             ('ebom', _('Engineering BoM'))],
                            _('BoM Type'),
                            required=True,
                            help=_("Phantom BOM: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product."
                                   " Ship this product as a set of components (kit)."))
    itemnum = fields.Integer(_('CAD Item Position'), help=_("This is the item reference position into the CAD document that declares this BoM."))
    itemlbl = fields.Char(_('CAD Item Position Label'), size=64)
    ebom_source_id = fields.Integer('Source Ebom ID')


MrpBomLineExtension()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
