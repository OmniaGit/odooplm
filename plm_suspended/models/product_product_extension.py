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

from odoo import api
from odoo import fields
from odoo import models

from odoo.addons.plm.models.product_product import USED_STATES
from odoo.addons.plm.models.product_product import USEDIC_STATES


class PlmComponentExtension(models.Model):
    _inherit = 'product.product'

    state = fields.Selection(USED_STATES,
                             _('Status'),
                             help=_("The status of the product."),
                             readonly="True",
                             default='draft',
                             required=True)
    old_state = fields.Char(size=128,
                            name=_("Old Staus"))

    @property
    def actions(self):
        actionDict = super(PlmComponentExtension, self).actions
        actionDict['suspended'] = self.action_suspend

    @api.multi
    def action_suspend(self):
        """
            reactivate the object
        """
        if self.ischecked_in():
            defaults = {}
            defaults['old_state'] = self.state
            defaults['state'] = 'suspended'
            self.setCheckContextWrite(False)
            objId = self.write(defaults)
            if objId:
                self.wf_message_post(body=_('Status moved to:%s.' % (USEDIC_STATES[defaults['state']])))
            return objId
        return False
