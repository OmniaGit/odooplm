##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import _, api, fields, models


class PlmBomReportWizard(models.TransientModel):
    _name = 'plm.bom.report.wizard'
    _description = 'PLM BoM Report Selection Wizard'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=True
    )

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        readonly=True
    )

    bom_type = fields.Selection([
        ('all', 'All'),
        ('normal', 'Normal BoM'),
        ('spbom', 'Spare BoM'),
        ('phantom', 'Kit'),
    ], string='BoM Type', default='all')

    available_bom_ids = fields.Many2many(
        'mrp.bom',
        compute='_compute_available_bom_ids',
        string='Available BoMs'
    )

    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        required=True,
        domain="[('id', 'in', available_bom_ids)]"
    )

    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        required=True,
        domain="[('model', 'in', ['mrp.bom', 'product.product'])]"
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        if active_model == 'product.product':
            product = self.env['product.product'].browse(active_id)

            res['product_id'] = product.id
            res['product_tmpl_id'] = product.product_tmpl_id.id
        elif active_model == 'product.template':
            template = self.env['product.template'].browse(active_id)

            res['product_tmpl_id'] = template.id

            if len(template.product_variant_ids) == 1:
                res['product_id'] = template.product_variant_ids.id
        default_report = self.env.ref(
            'mrp.action_report_bom_structure',
            raise_if_not_found=False
        )
        if default_report:
            res['report_id'] = default_report.id
        return res

    def _get_available_boms(self):
        self.ensure_one()
        MrpBom = self.env['mrp.bom']
        base_domain = [
            '|',
            ('product_id', '=', self.product_id.id),
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
        ]
        normal_boms = MrpBom.search(
            base_domain + [('type', '!=', 'spbom')]
        )
        component_products = normal_boms.mapped('bom_line_ids.product_id')
        spare_boms = MrpBom.search([
            ('type', '=', 'spbom'),
            (
                'product_tmpl_id',
                'in',
                component_products.mapped('product_tmpl_id').ids
            )
        ])

        if self.bom_type == 'normal':
            return normal_boms.filtered(
                lambda b: b.type == 'normal'
            )

        elif self.bom_type == 'phantom':
            return normal_boms.filtered(
                lambda b: b.type == 'phantom'
            )

        elif self.bom_type == 'spbom':
            return spare_boms

        elif self.bom_type == 'all':
            return normal_boms | spare_boms

        return normal_boms

    @api.depends('product_id', 'product_tmpl_id', 'bom_type')
    def _compute_available_bom_ids(self):
        for wizard in self:
            wizard.available_bom_ids = wizard._get_available_boms()

    @api.onchange('bom_type')
    def _onchange_bom_type(self):
        self.bom_id = False
        available_boms = self._get_available_boms()
        if available_boms:
            self.bom_id = available_boms[0].id

    def action_print_bom(self):
        self.ensure_one()
        if self.report_id.model == 'mrp.bom':
            return self.report_id.report_action(self.bom_id)
        return self.report_id.report_action(self.product_id)
