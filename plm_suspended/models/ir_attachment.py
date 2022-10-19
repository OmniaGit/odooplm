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
from odoo import _
from odoo import api
from odoo import models
from odoo import fields

from odoo.addons.plm.models.ir_attachment import USED_STATES

USED_STATES.append(('suspended', _('Suspended')))


class PlmDocumentExtension(models.Model):
    _inherit = 'ir.attachment'

    engineering_state = fields.Selection(USED_STATES,
                                         string='Status',
                                         help=_("The status of the product."),
                                         readonly="True",
                                         default='draft')
    old_state = fields.Char(
        name=_("Old Status")
    )

    @property
    def actions(self):
        action_dict = super(PlmDocumentExtension, self).actions
        action_dict['suspended'] = self.action_suspend
        return action_dict

    def action_suspend(self):
        """
            reactivate the object
        """
        if self.ischecked_in():
            defaults = {'old_state': self.engineering_state, 'engineering_state': 'suspended'}
            return self.with_context(check=False).write(defaults)
        return False

    def action_unsuspend(self):
        """
            reactivate the object
        """
        if self.ischecked_in():
            defaults = {'old_state': self.engineering_state, 'engineering_state': self.old_state}
            return self.with_context(check=False).write(defaults)
        return False

    @api.model
    def is_plm_state_writable(self):
        if super(PlmDocumentExtension, self).is_plm_state_writable():
            for customObject in self:
                if customObject.engineering_state in ('suspended',):
                    return False
            return True
        else:
            return False
