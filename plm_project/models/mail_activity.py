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
Created on 30 Aug 2016

@author: Daniel Smerghetto
"""
from odoo import models
from odoo import _
from odoo.exceptions import UserError


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=False):
        for activity in self:
            if self.checkProdConfirmedType(activity):
                if not self.checkSameUser(activity):
                    raise UserError(_('You cannot mark as done a "Product Confirmed" activity if is not assigned to you.'))
        messages, activities = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)
        for message in messages:
            if message.model == 'product.product':
                product = self.env[message.model].browse(message.res_id)
                if product.state == 'confirmed':
                    product.action_release()
        return messages, activities

    def checkProdConfirmedType(self, activity):
        if activity.activity_type_id == self.env.ref('plm_project.mail_activity_product_confirmed'):
            return True
        return False

    def checkSameUser(self, activity):
        if self.env.user == activity.user_id or self.env.user.has_group('plm.group_plm_admin'):
            return True
        return False

    def unlink(self):
        for activity in self:
            if self.checkProdConfirmedType(activity):
                if not self.checkSameUser(activity):
                    raise UserError(_('You cannot unlink a "Product Confirmed" activity if is not assigned to you.'))
        return super(MailActivity, self).unlink()

    def write(self, vals):
        for activity in self:
            if self.checkProdConfirmedType(activity):
                if not self.checkSameUser(activity):
                    raise UserError(_('You cannot edit a "Product Confirmed" activity if is not assigned to you.'))
        return super(MailActivity, self).write(vals)