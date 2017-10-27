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
Created on 30 Aug 2016

@author: Daniel Smerghetto
'''
from odoo import fields, models, _


class ProjectExtension(models.Model):
    _inherit = 'project.project'

    def _compute_plm_complete(self):
        """
        compute the percentage of the product completed
        """
        for project in self:
            if project.plm_product_ids:
                productOk = 0
                for product in project.plm_product_ids:
                    if product.state in ['released']:
                        productOk = productOk + 1
                project.plm_completed = round(100.0 * productOk / len(project.plm_product_ids), 2)
            else:
                project.plm_completed = 100

    def _compute_product_count(self):
        for project in self:
            project.plm_product_count = len(project.plm_product_ids)

    plm_use_plm = fields.Boolean(string='Use PLM',
                                 default=False,
                                 help=_("Check this box to manage plm data into project"))
    plm_completed = fields.Float(string=_('Plm Complete'),
                                 compute="_compute_plm_complete")
    plm_product_ids = fields.Many2many('product.product',
                                       'project_product_rel',
                                       'project_id',
                                       'product_id',
                                       string=_('Products'))
    plm_product_count = fields.Integer(compute='_compute_product_count',
                                       string=_("Number of product related"))
