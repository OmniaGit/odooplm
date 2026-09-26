# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""The groups a search answers under the odooPLM context.

res.groups.search shows only the PLM groups when odooPLM is in the context:
what a person is shown. Odoo's own permission check searches the groups as
superuser (res.users._get_group_definitions) and has to see all of them. When
it did not, the first check made with odooPLM in the context -- every call of
the CAD client carries it -- failed with a KeyError on a fresh server, and so
did every document create after it.
"""
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

#
# --test-tags=odoo_plm_groups   (post_install: no -u needed)
#


@tagged("-standard", "-at_install", "post_install", "odoo_plm_groups")
class PlmGroupsSearch(TransactionCase):

    def test_permission_check_with_the_client_context(self):
        # The definitions are cached per process whatever the context: empty
        # the cache, so the check below is the first one, as on a fresh server.
        self.env.registry.clear_cache("groups")
        admin = self.env.ref("base.user_admin").with_context(odooPLM=True)
        self.assertTrue(admin.has_group("base.group_user"))

    def test_a_person_still_sees_only_the_plm_groups(self):
        user = self.env["res.users"].create(
            {
                "name": "plm groups reader",
                "login": "plm_groups_reader",
                "groups_id": [Command.set([self.env.ref("base.group_user").id,
                                           self.env.ref("plm.group_plm_view_user").id])],
            }
        )
        groups = self.env["res.groups"].with_user(user)
        plm_only = groups.with_context(odooPLM=True).search([])
        everything = groups.search([])
        self.assertIn(self.env.ref("plm.group_plm_view_user"), plm_only)
        self.assertNotIn(self.env.ref("base.group_user"), plm_only)
        self.assertLess(len(plm_only), len(everything))
