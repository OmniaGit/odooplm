# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2020 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, models, fields

class PlmMarkupLog(models.Model):
    _name = 'plm.markup.log'
    _description = 'PLM 3D Markup Annotations'
    _order = 'create_date desc'

    comment     = fields.Text()
    snapshot    = fields.Binary()
    base_image = fields.Binary()
    filename    = fields.Char()
    canvas_data = fields.Text()
    res_id      = fields.Integer(string='Document ID', index=True)
    res_model   = fields.Char(string='Document Model')
    message_id = fields.Many2one('mail.message', string='Chatter Message', ondelete='set null')
    document_id = fields.Many2one(
        'ir.attachment',
        string='Document',
        compute='_compute_document_id',
        store=True,
        index=True,
        ondelete='cascade',
        help="The PLM document the markup was drawn on, when it was drawn on "
        "one. The record rule reads it: a markup is seen by whoever may see "
        "its document.",
    )

    @api.depends('res_model', 'res_id')
    def _compute_document_id(self):
        for markup in self:
            if markup.res_model == 'ir.attachment' and markup.res_id:
                markup.document_id = markup.res_id
            else:
                markup.document_id = False

