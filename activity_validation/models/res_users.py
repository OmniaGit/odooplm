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
from odoo import models
from odoo import api
from odoo import modules
from odoo import fields


class ResUsers(models.Model):
    _inherit = 'res.users'


    @api.model
    def systray_get_activities(self):
        """ Update the systray icon of res.partner activities to use the
        contact application one instead of base icon. """
        activities = super(ResUsers, self).systray_get_activities()
        for activity_dict in activities:
            model = activity_dict.get('model', '')
            if model and model in ['product.product', 'product.template']:
                mail_activity_id = self.env['mail.activity']
                today = fields.Date.context_today(self)
                today_count = mail_activity_id.search_count([('res_model', '=', model), ('plm_state', '!=', 'finished'), ('user_id', '=', self.env.uid), ('date_deadline', '=', today)])
                overdue_count = mail_activity_id.search_count([('res_model', '=', model), ('plm_state', '!=', 'finished'), ('user_id', '=', self.env.uid), ('date_deadline', '<', today)])
                planned_count = mail_activity_id.search_count([('res_model', '=', model), ('plm_state', '!=', 'finished'), ('user_id', '=', self.env.uid), ('date_deadline', '>', today)])
                activity_dict['total_count'] = today_count + overdue_count + planned_count
                activity_dict['overdue_count'] = overdue_count
                activity_dict['today_count'] = today_count
                activity_dict['planned_count'] = planned_count
        return activities

