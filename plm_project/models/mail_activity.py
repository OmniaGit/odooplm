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

"""
Created on 30 Aug 2016

@author: Daniel Smerghetto
"""
from odoo import fields, models, _
from datetime import datetime


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=False):
        messages, activities = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)
        for message in messages:
            if message.model == 'product.product':
                product = self.env[message.model].browse(message.res_id)
                if product.state == 'confirmed':
                    product.action_release()
        return messages, activities
