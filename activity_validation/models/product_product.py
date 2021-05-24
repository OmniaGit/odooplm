# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
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
'''
Created on Nov 16, 2019

@author: mboscolo
'''
import logging
import datetime
from odoo import SUPERUSER_ID
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('activity_ids.plm_state')
    def _compute_opened_activities(self):
        for product in self:
            product.opened_activities = False
            for activity in product.activity_ids:
                if activity.plm_state != 'finished':
                    product.opened_activities = True
                    break

    opened_activities = fields.Boolean(compute='_compute_opened_activities', store=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        from_activity = self.env.context.get('from_activity_counter', False)
        if from_activity == 1:
            domain.append(('opened_activities', '=', True))
        return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
