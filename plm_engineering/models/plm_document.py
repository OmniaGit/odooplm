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
Created on 31 Aug 2016

@author: Daniel Smerghetto
'''
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
USED_STATES = [('draft', _('Draft')),
               ('confirmed', _('Confirmed')),
               ('released', _('Released')),
               ('undermodify', _('UnderModify')),
               ('obsoleted', _('Obsoleted'))]
USEDIC_STATES = dict(USED_STATES)


class PlmDocument(models.Model):
    _inherit = 'plm.document'

    @api.multi
    def action_reactivate(self):
        """
            reactivate the object
        """
        defaults = {}
        defaults['engineering_writable'] = False
        defaults['state'] = 'released'
        if self.ischecked_in():
            self.setCheckContextWrite(False)
            objId = self.write(defaults)
            if objId:
                self.wf_message_post(body=_('Status moved to:%s.' % (USEDIC_STATES[defaults['state']])))
            return objId
        return False

PlmDocument()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
