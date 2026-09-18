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
"""What each PLM group may do with a document.

Which documents a user reaches is decided by the plm.access node they hang from
(see test_multicompany_access); this is the other half: what the PLM groups
themselves allow on a document already in reach. The two are independent, and a
user needs both.
"""
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

#
# --test-tags=odoo_plm_security
#


@tagged("-standard", "odoo_plm_security")
class PlmSecurityRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.node = cls.company.plm_access_id

        def make_user(login, plm_group_xmlid):
            groups = cls.env.ref("base.group_user")
            if plm_group_xmlid:
                groups |= cls.env.ref(plm_group_xmlid)
            return cls.env["res.users"].create(
                {
                    "name": login,
                    "login": login,
                    "email": "%s@example.com" % login,
                    "company_id": cls.company.id,
                    "company_ids": [Command.set(cls.company.ids)],
                    "groups_id": [Command.set(groups.ids)],
                }
            )

        cls.user_none = make_user("plm_sec_none", None)
        cls.user_view = make_user("plm_sec_view", "plm.group_plm_view_user")
        cls.user_integration = make_user(
            "plm_sec_integration", "plm.group_plm_integration_user"
        )
        cls.user_admin = make_user("plm_sec_admin", "plm.group_plm_admin")
        cls.document = cls._plm_doc("doc_sec")

    @classmethod
    def _plm_doc(cls, name):
        """The company of a PLM document comes from the access node it hangs
        from, so the node is what the document is created with."""
        return cls.env["ir.attachment"].create(
            {
                "name": name,
                "datas": DUMMY_CONTENT,
                "document_type": "3d",
                "engineering_code": "EC_" + name,
                "engineering_state": "draft",
                "is_plm": True,
                "plm_access_id": cls.node.id,
            }
        )

    def _as(self, user):
        return self.env["ir.attachment"].with_user(user).browse(self.document.id)

    def test_a_user_outside_the_plm_groups_is_refused_a_direct_read(self):
        """Searching filters the document out silently; reading it by id has to
        say no, or a link or an id guessed from elsewhere would hand it over."""
        with self.assertRaises(AccessError):
            self.document.with_user(self.user_none).read(["name"])

    def test_the_view_level_reads_but_does_not_write(self):
        self.assertEqual(self._as(self.user_view).name, "doc_sec")
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(
            AccessError
        ):
            self._as(self.user_view).write({"name": "written_by_view"})

    def test_the_integration_level_does_not_delete(self):
        """It reads, writes and creates; deleting is the administrator's."""
        self._as(self.user_integration).write({"desc_modify": "written_by_integration"})
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(
            AccessError
        ):
            self._as(self.user_integration).unlink()

    def test_the_admin_level_deletes(self):
        document = self._plm_doc("doc_sec_delete")
        self.env["ir.attachment"].with_user(self.user_admin).browse(
            document.id
        ).unlink()
        self.assertFalse(document.exists())
