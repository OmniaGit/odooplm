##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 03/nov/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
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
Created on 03/nov/2016

@author: mboscolo
'''

from openerp.exceptions import UserError
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
import logging


class plm_document(models.Model):
    _inherit = 'plm.document'

    @api.multi
    def show_convert_wizard(self):
        context = dict(self.env.context or {})
        context['default_document_id'] = self.id
        context['datas_fname'] = self.datas_fname
        out = {'view_type': 'form',
               'view_mode': 'form',
               'res_model': 'plm.convert',
               'view_id': self.env.ref('plm_automated_convertion.act_plm_convert_form').id,
               'type': 'ir.actions.act_window',
               'context': context,
               'target': 'new'
               }
        return out
