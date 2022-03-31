# -*- encoding: utf-8 -*-
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

'''
Created on 28 March 2022

@author: Daniel Smerghetto
'''
from odoo.osv.expression import AND
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.context.get('odooPLM'):
            available_types = [
                self.env.ref('plm.group_plm_view_user').id,
                self.env.ref('plm.group_plm_integration_user').id,
                self.env.ref('plm.group_plm_admin').id,
                self.env.ref('plm.group_plm_readonly_released').id,
                self.env.ref('plm.group_plm_release_users').id,
                ]
            additional_xml_refs = [
                'plm_automatic_weight.group_plm_weight_admin',
                'activity_validation.group_force_activity_validation_admin',
                'activity_validation.group_force_activity_validation_user',
                'activity_validation.group_force_activity_validation_user_readonly',
                ]
            for additional_xml_ref in additional_xml_refs:
                additional_obj = self.env.ref(additional_xml_ref, False)
                if additional_obj:
                    available_types.append(additional_obj.id)
            args = AND([args, [('id', 'in', available_types)]])
        return super(ResGroups, self).search(args, offset, limit, order, count)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: