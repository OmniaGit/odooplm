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
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
import logging
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging


class MrpBomLineExtension(models.Model):
    _inherit = 'mrp.bom.line'
    _order = "itemnum"


    def read(self, fields=[], load='_classic_read'):
        fields = self.plm_sanitize(fields)
        return super(MrpBomLineExtension, self).read(fields=fields, load=load)

    @api.model
    def create(self, vals):
        vals = self.plm_sanitize(vals)
        return super(MrpBomLineExtension, self).create(vals)

    def write(self, vals):
        vals = self.plm_sanitize(vals)
        ret = super(MrpBomLineExtension, self).write(vals)
        for line in self:
            line.bom_id.rebase_bom_weight()
        return ret

    def _get_child_bom_lines(self):
        """
            If the BOM line refers to a BOM, return the ids of the child BOM lines
        """
        bom_obj = self.env['mrp.bom']
        for bom_line in self:
            for bom_id in self.search(
                    [('product_id', '=', bom_line.product_id.id),
                     ('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                     ('type', '=', bom_line.type)]
            ):
                child_bom = bom_obj.browse(bom_id)
                for child_bom_line in child_bom.bom_line_ids:
                    child_bom_line._get_child_bom_lines()
                self.child_line_ids = [x.id for x in child_bom.bom_line_ids]
                return
            else:
                self.child_line_ids = False

    
    def get_related_boms(self):
        for bom_line in self:
            if not bom_line.product_id:
                bom_line.related_bom_id = []
            else:
                if not bom_line.hasChildBoms:
                    return []
                return self.env['mrp.bom'].search([
                    ('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                    ('type', '=', bom_line.type),
                    ('active', '=', True)
                ])

    @api.depends('product_id')
    def _has_children_boms(self):
        for bom_line in self:
            if not bom_line.product_id:
                bom_line.hasChildBoms = False
            else:
                num_boms = self.env['mrp.bom'].search_count([
                    ('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                    ('type', '=', bom_line.type),
                    ('active', '=', True)
                ])
                if num_boms:
                    bom_line.hasChildBoms = True
                else:
                    bom_line.hasChildBoms = False

    @api.depends('product_id')
    def _related_boms(self):
        for bom_line in self:
            if not bom_line.product_id:
                bom_line.related_bom_ids = [(5, False, False)]
            else:
                bom_objs = self.env['mrp.bom'].search([
                    ('product_tmpl_id', '=', bom_line.product_id.product_tmpl_id.id),
                    ('type', '=', bom_line.type),
                    ('active', '=', True)
                ])
                if not bom_objs:
                    bom_line.related_bom_ids = [(5, False, False)]
                else:
                    bom_line.related_bom_ids = [(6, False, bom_objs.ids)]

    
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

    
    def openRelatedDocuments(self):
        domain = [('id', 'in', self.related_document_ids.ids)]
        out_act_dict = {'name': _('Documents'),
                        'res_model': 'ir.attachment',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'kanban,tree,form',
                        'views': [
                            (self.env.ref('plm.document_kanban_view').id, 'kanban'),
                            (self.env.ref('plm.view_attachment_form_plm_hinerit').id, 'form'),
                            (self.env.ref('plm.ir_attachment_tree').id, 'tree'),
                            ],
                        'domain': domain}
        return out_act_dict

    
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
    source_id = fields.Many2one('ir.attachment',
                                'engineering_document_name',
                                ondelete='no action',
                                readonly=True,
                                index=True,
                                help=_("This is the document object that declares this BoM."))
    type = fields.Selection(related="bom_id.type")
    itemnum = fields.Integer(_('CAD Item Position'), help=_(
        "This is the item reference position into the CAD document that declares this BoM."))
    itemlbl = fields.Char(_('CAD Item Position Label'), size=64)

    engineering_revision = fields.Integer(related="product_id.engineering_revision",
                                          string=_("Revision"),
                                          help=_("The revision of the product."),
                                          store=False)
    hasChildBoms = fields.Boolean(compute='_has_children_boms',
                                  string='Has Children Boms')
    related_bom_ids = fields.One2many(compute='_related_boms',
                                      comodel_name='mrp.bom',
                                      string='Related BOMs',
                                      readonly=True)
    related_document_ids = fields.One2many(compute='_related_doc_ids',
                                           comodel_name='ir.attachment',
                                           string=_('Related Documents'))
    cutted_type = fields.Selection(
        [('none', 'None'),
         ('client', 'Client'),
         ('server', 'Server')],
        _('Cutted Compute Type'),
        default='none')

    def plm_sanitize(self, vals):
        all_keys = self._fields
        if isinstance(vals, dict):
            valsKey = list(vals.keys())
            for k in valsKey:
                if k not in all_keys:
                    del vals[k]
            return vals
        else:
            out = []
            for k in vals:
                if k in all_keys:
                    out.append(k)
            return out