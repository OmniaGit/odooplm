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
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    plm_state = fields.Selection([
        ('cancel', _('Cancel')),
        ('exception', _('Exception')),
        ('eco', _('Change Order')),
        ('done', _('Done')),
        ('in_progress', _('In Progress')),
        ('draft', _('draft')),
        ],
        default='draft',
        string=_('Plm State'))
    children_ids = fields.One2many('mail.activity.children.rel',
                                   'mail_parent_activity_id',
                                   _('ECR Activities'))
    name = fields.Char('Name')
    change_activity_type = fields.Selection(related='activity_type_id.change_activity_type')
    has_parent = fields.Boolean(_('Has parent ECR'), compute="_compute_has_parent_ecr", store=True)
    has_parent_eco = fields.Boolean(_('Has parent ECO'), compute="_compute_has_parent_eco", store=True)
    eco_child_ids = fields.One2many('mail.activity',
                                   'mail_parent_eco_activity_id',
                                   _('ECO Activities'))
    mail_parent_eco_activity_id = fields.Many2one('mail.activity', _('ECO Parent Activity'))
    default_plm_activity = fields.Many2one('mail.activity.type', compute='_compute_mail_activity_type')
    is_eco = fields.Boolean(_('Is ECO'))

    def _compute_mail_activity_type(self):
        for activity_id in self:
            activity_id.default_plm_activity = self.env.ref('plm.mail_activity_plm_activity')
        
    def getParentECRActivity(self, activity_id):
        parent_activity = self.env['mail.activity.children.rel'].search([('mail_children_activity_id', '=', activity_id.id)])
        return parent_activity.mapped('mail_parent_activity_id')

    def getParentECOActivity(self, activity_id):
        return activity_id.mail_parent_eco_activity_id

    @api.depends('children_ids')
    def _compute_has_parent_ecr(self):
        for activity_id in self:
            activities = self.getParentECRActivity(activity_id)
            if not activities:
                activity_id.has_parent = False
            else:
                activity_id.has_parent = True

    @api.depends('children_ids')
    def _compute_has_parent_eco(self):
        for activity_id in self:
            activities = self.getParentECOActivity(activity_id)
            if not activities:
                activity_id.has_parent_eco = False
            else:
                activity_id.has_parent_eco = True

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
            if activity_id.plm_state == 'done' and 'plm_state' not in vals:
                raise UserError('You cannot modify a confirmed activity')
        return ret

    def checkConfirmed(self, check=False):
        if self.env.user.has_group('activity_validation.group_force_activity_validation_admin'):
            return
        for activity_id in self:
            if check and activity_id.plm_state not in ['done', 'eco']:
                raise UserError('Cannot confirm activity because some activities are not done.')
            for child in activity_id.children_ids:
                child.mail_children_activity_id.checkConfirmed(True)

    def action_done(self):
        ret = super(MailActivity, self).action_done()
        if self.exists():
            self.checkConfirmed()
            self.plm_state = 'done'
        return ret

    def action_done_schedule_next(self):
        ret = super(MailActivity, self).action_done_schedule_next()
        if self.exists():
            self.checkConfirmed()
            self.plm_state = 'done'
        return ret

    def action_feedback(self, feedback=False, attachment_ids=None):
        for activity_id in self:
            if activity_id.exists():
                activity_id.plm_state = 'done'
                if activity_id.mail_parent_eco_activity_id:
                    close = True
                    for child in activity_id.mail_parent_eco_activity_id.eco_child_ids:
                        if child.plm_state != 'done':
                            close = False
                    if close:
                        activity_id.mail_parent_eco_activity_id.action_to_eco()
        ret = super(MailActivity, self).action_feedback(feedback, attachment_ids)
        return ret

    def activity_format(self):
        out = []
        for res_dict in super(MailActivity, self).activity_format():
            if res_dict.get('plm_state', 'draft') not in ['done', 'cancel']:
                out.append(res_dict)
        return out

    def isCustomType(self):
        for activity_id in self:
            if activity_id.activity_type_id.change_activity_type in ['request', 'plm_activity']:
                return True
        return False
        
    def unlink(self):
        for activity_id in self:
            if activity_id.isCustomType():
                if not self.env.su:
                    return
        return super(MailActivity, self).unlink()

    def clearChildrenActivities(self):
        for child_id in self.children_ids:
            for child_rel in child_id.mail_children_activity_id.sudo():
                if child_rel.mail_children_activity_id.plm_state == 'draft':
                    child_rel.mail_children_activity_id.unlink()
                    child_rel.unlink()

    def action_to_draft(self):
        self.clearChildrenActivities()
        self.changeActivityTypeId()
        for activity_id in self:
            activity_id.plm_state = 'draft'
            return self.reopenActivity(activity_id.id)

    def action_to_done(self):
        for activity_id in self:
            activity_id.plm_state = 'done'
            if activity_id.is_eco:
                self.checkChildrenECODone(activity_id)
                parents = self.getParentECOActivity(activity_id)
            else:
                self.checkChildrenECRDone(activity_id)
                parents = self.getParentECRActivity(activity_id)
            close = True
            if parents.children_ids:
                for child_activity_id in parents.children_ids:
                    if child_activity_id.plm_state != 'done':
                        close = False
                if close:
                    parents._action_done()
            else:
                activity_id._action_done()

    def action_to_exception(self):
        for activity_id in self:
            activity_id.plm_state = 'exception'
            if not activity_id.is_eco:
                parents = self.getParentECRActivity(activity_id)
            else:
                parents = self.getParentECOActivity(activity_id)
            parents.plm_state = 'exception'
            return self.reopenActivity(activity_id.id)

    def action_to_cancel(self):
        for activity_id in self:
            activity_id.plm_state = 'cancel'
            self.cancelChildrenECO(activity_id)
            self.cancelChildrenECR(activity_id)
            activity_id._action_done()

    def cancelChildrenECR(self, activity_id):
        for child in activity_id.children_ids:
            if child.plm_state not in ['done', 'cancel']:
                child.action_to_cancel()

    def cancelChildrenECO(self, activity_id):
        for child in activity_id.children_ids:
            if child.plm_state not in ['done', 'cancel']:
                child.mail_children_activity_id.action_to_cancel()

    def checkChildrenECODone(self, activity_id):
        do_eco = True
        for child in activity_id.eco_child_ids:
            if child.plm_state not in ['done', 'cancel']:
                do_eco = False
        if not do_eco:
            raise UserError(_('You cannot move to Done because there are pending ECO activities.'))

    def checkChildrenECRDone(self, activity_id):
        do_ecr = True
        for child in activity_id.children_ids:
            if child.plm_state not in ['done', 'cancel']:
                do_ecr = False
        if not do_ecr:
            raise UserError(_('You cannot move to ECO or to Done because there are pending ECR activities.'))

    def action_to_eco(self):
        for activity_id in self:
            self.checkChildrenECRDone(activity_id)
            activity_id.plm_state = 'eco'
            activity_id.is_eco = True

    def action_in_progress(self):
        for activity_id in self:
            for line_id in activity_id.children_ids:
                if not line_id.mail_children_activity_id:
                    activity_vals = {
                        'activity_type_id': activity_id.activity_type_id.id,
                        'date_deadline': activity_id.date_deadline,
                        'user_id': line_id.user_id.id,
                        'plm_state': 'draft',
                        'name': line_id.name,
                        'note': line_id.name,
                        'res_model_id': activity_id.res_model_id.id,
                        'res_id': activity_id.res_id,
                        }
                    new_activity_id = self.create(activity_vals)
                    line_id.mail_children_activity_id = new_activity_id.id
                    line_id.mail_parent_activity_id = activity_id.id
            activity_id.plm_state = 'in_progress'
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

    def name_get(self):
        out = []
        for activity in self:
            name = '%s | %s' % (activity.summary or activity.activity_type_id.display_name, activity.user_id.display_name or '')
            out.append((activity.id, name))
        return out

    @api.model
    def create(self, vals):
        return super(MailActivity, self).create(vals)
