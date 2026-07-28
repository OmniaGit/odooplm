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

"""
Created on 28 March 2022

@author: Daniel Smerghetto
"""
from odoo import models, api


class ResGroups(models.Model):
    _inherit = "res.groups"

    @api.model
    def _get_view_group_hierarchy(self):
        if not self.env.context.get("odooPLM"):
            return super()._get_view_group_hierarchy()

        res = super(ResGroups, self.with_context(odooPLM=False))._get_view_group_hierarchy()

        available_types = self._get_plm_available_groups()
        allowed_group_ids = set(available_types)

        res['groups'] = {gid: gdata for gid, gdata in res['groups'].items() if gid in allowed_group_ids}

        new_privileges = {}
        for pid, pdata in res['privileges'].items():
            filtered_group_ids = [gid for gid in pdata['group_ids'] if gid in allowed_group_ids]
            if filtered_group_ids:
                pdata['group_ids'] = filtered_group_ids
                new_privileges[pid] = pdata
        res['privileges'] = new_privileges

        new_categories = []
        allowed_privilege_ids = set(new_privileges.keys())
        for cat in res['categories']:
            filtered_priv_ids = [pid for pid in cat['privilege_ids'] if pid in allowed_privilege_ids]
            if filtered_priv_ids:
                cat['privilege_ids'] = filtered_priv_ids
                new_categories.append(cat)
        res['categories'] = new_categories

        return res

    def _get_plm_available_groups(self):
        available_types = [
            self.env.ref("plm.group_plm_view_user").id,
            self.env.ref("plm.group_plm_integration_user").id,
            self.env.ref("plm.group_plm_admin").id,
            self.env.ref("plm.group_plm_readonly_released").id,
            self.env.ref("plm.group_plm_release_users").id,
        ]
        additional_xml_refs = [
            "plm_automatic_weight.group_plm_weight_admin",
            "activity_validation.group_force_activity_validation_admin",
            "activity_validation.group_force_activity_validation_user",
            "activity_validation.group_force_activity_validation_user_readonly",
        ]
        for additional_xml_ref in additional_xml_refs:
            additional_obj = self.env.ref(additional_xml_ref, False)
            if additional_obj:
                available_types.append(additional_obj.id)
        return available_types


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
