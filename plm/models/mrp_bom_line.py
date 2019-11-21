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

"""
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


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

    @api.multi
    def get_related_boms(self):
        for bom_line in self:
            if not self.product_id:
                self.related_bom_id = []
            else:
                if not self.hasChildBoms:
                    return []
                return self.env['mrp.bom'].search([('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                                                   ('type', '=', bom_line.type),
                                                   ('active', '=', True)
                                                   ])

    @api.one
    @api.depends('product_id')
    def _has_children_boms(self):
        for bom_line in self:
            if not self.product_id:
                self.hasChildBoms = False
            else:
                num_boms = self.env['mrp.bom'].search_count([
                    ('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                    ('type', '=', bom_line.type),
                    ('active', '=', True)
                ])
                if num_boms:
                    self.hasChildBoms = True
                else:
                    self.hasChildBoms = False

    @api.one
    @api.depends('product_id')
    def _related_boms(self):
        for bom_line in self:
            if not self.product_id:
                self.related_bom_id = []
            else:
                bom_objs = self.env['mrp.bom'].search([
                    ('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                    ('type', '=', bom_line.type),
                    ('active', '=', True)
                ])
                if not bom_objs:
                    self.related_bom_ids = []
                else:
                    self.related_bom_ids = bom_objs.ids

    @api.multi
    def openRelatedBoms(self):
        related_boms = self.get_related_boms()
        if not related_boms:
            raise UserError(_("There aren't related boms to this line."))
        ids_to_open = []
        for brws in related_boms:
            ids_to_open.append(brws.id)
        domain = [('id', 'in', ids_to_open)]
        out_act_dict = {'name': _('B.o.M.'),
                        'view_type': 'form',
                        'res_model': 'mrp.bom',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'tree,form'}
        if len(ids_to_open) == 1:
            out_act_dict['view_mode'] = 'form'
            out_act_dict['res_id'] = ids_to_open[0]
        for line_brws in self:
            if line_brws.type == 'normal':
                domain.append(('type', '=', 'normal'))
            elif line_brws.type == 'ebom':
                domain.append(('type', '=', 'ebom'))
                out_act_dict['view_ids'] = [
                    (5, 0, 0),
                    (0, 0, {'view_mode': 'tree', 'view_id': self.env.ref('plm.plm_bom_tree_view').id}),
                    (0, 0, {'view_mode': 'form', 'view_id': self.env.ref('plm.plm_bom_form_view').id})
                ]
            elif line_brws.type == 'spbom':
                domain.append(('type', '=', 'spbom'))
        out_act_dict['domain'] = domain
        return out_act_dict

    @api.multi
    def openRelatedDocuments(self):
        domain = [('id', 'in', self.related_document_ids.ids)]
        outActDict = {'name': _('Documents'),
                      'view_type': 'form',
                      'res_model': 'plm.document',
                      'type': 'ir.actions.act_window',
                      'view_mode': 'kanban,tree,form'}
        outActDict['domain'] = domain
        return outActDict

    @api.multi
    def _related_doc_ids(self):
        for bom_line_brws in self:
            bom_line_brws.related_document_ids = bom_line_brws.product_id.linkeddocuments

    state = fields.Selection(related="product_id.state",
                             string=_("Status"),
                             help=_("The status of the product in its LifeCycle."),
                             store=False)
    description = fields.Char(related="product_id.name",
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
    type = fields.Selection(
        [('normal', _('Normal BoM')),
         ('phantom', _('Sets / Phantom'))],
        _('BoM Type'),
        required=True,
        help=_(
            "Phantom BOM: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product."
            " Ship this product as a set of components (kit).")
    )
    itemnum = fields.Integer(_('CAD Item Position'), help=_(
        "This is the item reference position into the CAD document that declares this BoM."))
    itemlbl = fields.Char(_('CAD Item Position Label'), size=64)

    engineering_revision = fields.Integer(related="product_id.engineering_revision",
                                          string=_("Revision"),
                                          help=_("The revision of the product."),
                                          store=False)

    engineering_code = fields.Char(related="product_id.engineering_code",
                                   string=_("E-Cod"),
                                   help=_("The Engineering Rivision code."),
                                   store=False)

    hasChildBoms = fields.Boolean(compute='_has_children_boms',
                                  string='Has Children Boms')
    related_bom_ids = fields.One2many(compute='_related_boms',
                                      comodel_name='mrp.bom',
                                      string='Related BOMs',
                                      digits=0,
                                      readonly=True)
    related_document_ids = fields.One2many(compute='_related_doc_ids',
                                           comodel_name='plm.document',
                                           string=_('Related Documents'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
