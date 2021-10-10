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
from odoo import fields
from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @property
    def actions(self):
        action_dict = super(ProductProduct, self).actions
        action_dict['suspended'] = self.action_suspend
        return action_dict

    def action_suspend(self):
        """
            reactivate the object
        """
        defaults = {'old_state': self.state, 'state': 'suspended'}
        obj_id = self.write(defaults)
        self.product_tmpl_id.write(defaults)
        if obj_id:
            self.wf_message_post(body=_('Status moved to:{}.'.format(defaults['state'])))
        return obj_id

    def action_unsuspend(self):
        """
            reactivate the object
        """
        defaults = {'old_state': self.state, 'state': self.old_state}
        obj_id = self.write(defaults)
        self.product_tmpl_id.write(defaults)
        if obj_id:
            self.wf_message_post(body=_('Status moved to:{}.'.format(defaults['state'])))
        return obj_id
