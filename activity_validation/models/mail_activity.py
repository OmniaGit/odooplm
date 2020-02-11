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
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    plm_state = fields.Selection([('draft', _('draft')),
                                  ('send_request', _('Send Request')),
                                  ('reject_request', _('Reject Request')),
                                  ('need_review', _('Need Review')),
                                  ('confirmed', _('confirmed')),
                                  ],
                                  default='draft',
                                 string=_('Plm State'))
    children_ids = fields.Many2many('mail.activity.children.rel',
                                    'activity_id_children_rel',
                                    'activity_id',
                                    'child_activity_obj_id',
                                    _('Children Activities'))
    name = fields.Char('Name')

    @api.onchange('activity_type_id')
    def changeActivityTypeId(self):
        for activity_id in self:
            activity_ids = []
            if activity_id.isCustomType():
                for user_id in activity_id.activity_type_id.activity_user_ids:
                    vals = {
                        'name': '%s - %s' % (activity_id.activity_type_id.name, user_id.name),
                        'user_id': user_id.id,
                        'mail_children_activity_id': False,
                        }
                    rel_id = self.env['mail.activity.children.rel'].create(vals)
                    activity_ids.append(rel_id.id)
            activity_id.write({
                'children_ids': [(6, False, activity_ids)]
                })

    def write(self, vals):
        ret = super(MailActivity, self).write(vals)
        for activity_id in self:
            if self.env.user.has_group('activity_validation.group_force_activity_validation_admin'):
                return ret
            if activity_id.plm_state == 'confirmed':
                raise UserError('You cannot modify a confirmed activity')
        return ret
        

    def action_close_dialog(self):
        for line_id in self.children_ids:
            if not line_id.mail_children_activity_id:
                activity_vals = {
                    'activity_type_id': self.activity_type_id.id,
                    'date_deadline': self.date_deadline,
                    'user_id': line_id.user_id.id,
                    'plm_state': 'send_request',
                    'name': line_id.name,
                    }
                new_activity_id = self.create(activity_vals)
                line_id.mail_children_activity_id = new_activity_id.id
        return {'type': 'ir.actions.act_window_close'}

    def checkConfirmed(self, check=False):
        if self.env.user.has_group('activity_validation.group_force_activity_validation_admin'):
            return
        for activity_id in self:
            if check and activity_id.plm_state != 'confirmed':
                raise UserError('Cannot confirm activity because some activities are not done.')
            for child in activity_id.children_ids:
                child.mail_children_activity_id.checkConfirmed(True)

    def action_done(self):
        self.checkConfirmed()
        self.plm_state = 'confirmed'
        return super(MailActivity, self).action_done()

    def action_done_schedule_next(self):
        self.checkConfirmed()
        self.plm_state = 'confirmed'
        return super(MailActivity, self).action_done_schedule_next()

    def activity_format(self):
        out = []
        for res_dict in super(MailActivity, self).activity_format():
            if res_dict.get('plm_state', 'draft') not in ['confirmed', 'reject_request']:
                out.append(res_dict)
        return out

    def isCustomType(self):
        for activity_id in self:
            if activity_id.activity_type_id.change_activity_type in ['request', 'order']:
                return True
        return False
        
    def unlink(self):
        for activity_id in self:
            if activity_id.isCustomType():
                return
        return super(MailActivity, self).unlink()

    def action_confirm(self):
        for activity_id in self:
            activity_id.plm_state = 'confirmed'
            return self.reopenActivity(activity_id.id)

    def action_reject(self):
        for activity_id in self:
            activity_id.plm_state = 'reject_request'
            return self.reopenActivity(activity_id.id)

    def action_need_review(self):
        for activity_id in self:
            activity_id.plm_state = 'need_review'
            return self.reopenActivity(activity_id.id)

    def action_send_request(self):
        for activity_id in self:
            activity_id.plm_state = 'send_request'
            return self.reopenActivity(activity_id.id)

    def reopenActivity(self, res_id):
        out_act_dict = {'name': _('Activity'),
                        'view_type': 'form',
                        'target': 'new',
                        'res_model': 'mail.activity',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_id': res_id}
        return out_act_dict
