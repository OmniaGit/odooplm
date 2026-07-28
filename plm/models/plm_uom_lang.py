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

from odoo import models
from odoo import fields
from odoo import api


class PlmUomLang(models.Model):
    _name = 'plm.uom.lang'
    _description = 'Per-language report Unit of Measure'
    _rec_name = 'uom_id'

    lang_id = fields.Many2one('res.lang',
                              string='Language',
                              required=True,
                              ondelete='cascade')
    category_id = fields.Many2one('uom.category',
                                  string='Unit Category',
                                  required=True,
                                  ondelete='cascade')
    uom_id = fields.Many2one('uom.uom',
                             string='Report Unit of Measure',
                             required=True,
                             domain="[('category_id', '=', category_id)]")

    _sql_constraints = [
        ('lang_category_uniq',
         'unique(lang_id, category_id)',
         'A language can define only one report unit of measure per unit category.'),
    ]

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.uom_id and self.uom_id.category_id != self.category_id:
            self.uom_id = False

    @api.model
    def _get_report_target_uom(self, lang_code, category):
        """Return the report UoM to use for the given language code and unit
        category, or an empty ``uom.uom`` recordset when none applies.

        Resolution order:

        1. the row configured for ``lang_code`` and ``category``;
        2. otherwise the row configured for the language flagged as the report
           default (``res.lang.plm_report_uom_default``) for that ``category``.

        Read with ``sudo`` so the conversion also works while a report is being
        rendered by a user who has no direct access to this configuration model.
        """
        if not category:
            return self.env['uom.uom']
        model = self.sudo()
        if lang_code:
            record = model.search([('lang_id.code', '=', lang_code),
                                   ('category_id', '=', category.id)], limit=1)
            if record:
                return record.uom_id
        default_lang = self.env['res.lang'].sudo().search(
            [('plm_report_uom_default', '=', True)], limit=1)
        if default_lang and default_lang.code != lang_code:
            record = model.search([('lang_id', '=', default_lang.id),
                                   ('category_id', '=', category.id)], limit=1)
            if record:
                return record.uom_id
        return self.env['uom.uom']


class ResLang(models.Model):
    _inherit = 'res.lang'

    plm_report_uom_ids = fields.One2many('plm.uom.lang',
                                         'lang_id',
                                         string='Report Units of Measure')
    plm_report_uom_default = fields.Boolean(
        string='Default for Report Units',
        help="When a printed report is rendered in a language that has no report "
             "unit of measure configured for a given unit category, the "
             "configuration of the language flagged here is used as a fallback. "
             "Only one language should be flagged.")

    def _plm_enforce_single_report_default(self):
        """Ensure at most one language is flagged as the report-units default."""
        keep = self.filtered('plm_report_uom_default')[-1:]
        if not keep:
            return
        others = self.search([('plm_report_uom_default', '=', True),
                              ('id', '!=', keep.id)])
        if others:
            others.write({'plm_report_uom_default': False})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(vals.get('plm_report_uom_default') for vals in vals_list):
            records._plm_enforce_single_report_default()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('plm_report_uom_default'):
            self._plm_enforce_single_report_default()
        return res
