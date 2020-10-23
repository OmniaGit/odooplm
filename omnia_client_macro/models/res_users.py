# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution    
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
Created on Apr 19, 2017

@author: daniel
'''

from odoo import models, fields, api
import logging


class ResUsersExt(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    macro_ids = fields.Many2many('client.macro', 'user_macro_rel', 
                         'macro_id', 'user_id', string='Macros')

    @api.multi
    def getMacros(self):
        logging.info('Request macros for user %r' % (self.env.uid))
        for userBrws in self.browse(self.env.uid):
            logging.info('Request Macros file for user %r' % (userBrws.env.uid))
            if userBrws.macro_ids:
                return userBrws.macro_ids.getMacrosInfos()
            else:
                for groupBrws in userBrws.groups_id:
                    out = groupBrws.getMacros()
                    if not out:
                        continue
                    else:
                        return out
        return []

    @api.multi
    def getMacroUserInfos(self):
        logging.info('Request macros for user %r' % (self.env.uid))
        for userBrws in self.browse(self.env.uid):
            logging.info('Request Macros info for user %r' % (userBrws.env.uid))
            if userBrws.macro_ids:
                return userBrws.macro_ids.getMacroUserInfos()
            else:
                for groupBrws in userBrws.groups_id:
                    out = groupBrws.getMacroUserInfos()
                    if not out:
                        continue
                    else:
                        return out
        return []
