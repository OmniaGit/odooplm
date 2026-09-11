##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solution
#    Copyright (C) 2011-2022 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Access-control tests for PLM documents (ir.attachment, is_plm = True).

These tests validate the four-tier PLM security model. Unlike the rest of the
suite (which runs as SUPERUSER_ID and therefore bypasses every record rule and
the ir.attachment.check() override), each test here runs as a *real* non-super
user in a specific PLM group, with an explicit multi-company setup, so the
record rules are actually exercised.

Rules under test:
  1. A user in NO PLM group can never see an is_plm document (system-wide).
  2. group_plm_view_user     -> READ is_plm within company scope, no write;
                                and NOT the PLM application menu.
  3. group_plm_integration_user -> READ/WRITE/CREATE is_plm within company scope,
                                no delete.
  4. group_plm_admin         -> full access to every is_plm document, ignoring
                                the company visibility rule.

    --test-tags=odoo_plm_security
"""
from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

# Denials come from the record rules (AccessError) but the ir.attachment.check()
# backstop raises UserError; accept either so the tests assert *behaviour*.
ACCESS_DENIED = (AccessError, UserError)


@tagged("-standard", "odoo_plm_security")
class PlmSecurityRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "PLM Sec Co B"})

        group_user = cls.env.ref("base.group_user")

        def make_user(login, plm_group_xmlid):
            groups = [group_user.id]
            if plm_group_xmlid:
                groups.append(cls.env.ref(plm_group_xmlid).id)
            return cls.env["res.users"].create(
                {
                    "name": login,
                    "login": login,
                    "email": "%s@example.com" % login,
                    "company_id": cls.company_a.id,
                    "company_ids": [Command.set([cls.company_a.id])],
                    "groups_id": [Command.set(groups)],
                }
            )

        # All users belong to company_a ONLY (admin included -> proves bypass).
        cls.user_none = make_user("plm_sec_none", None)
        cls.user_view = make_user("plm_sec_view", "plm.group_plm_view_user")
        cls.user_integration = make_user(
            "plm_sec_integration", "plm.group_plm_integration_user"
        )
        cls.user_admin = make_user("plm_sec_admin", "plm.group_plm_admin")

        # Documents. Created as superuser without the odooPLM context, so create()
        # takes the plain super() path and the given fields are stored verbatim.
        cls.doc_a_own = cls._plm_doc("doc_a_own", cls.company_a, "own")
        cls.doc_b_own = cls._plm_doc("doc_b_own", cls.company_b, "own")
        cls.doc_b_all = cls._plm_doc("doc_b_all", cls.company_b, "all")
        cls.doc_nonplm = cls.env["ir.attachment"].create(
            {
                "name": "doc_nonplm",
                "datas": DUMMY_CONTENT,
                "res_model": "ir.attachment",
                "res_id": 0,
                "company_id": cls.company_a.id,
            }
        )

    @classmethod
    def _plm_doc(cls, name, company, scope):
        return cls.env["ir.attachment"].create(
            {
                "name": name,
                "datas": DUMMY_CONTENT,
                "res_model": "ir.attachment",
                "res_id": 0,
                "document_type": "3d",
                "engineering_code": "EC_" + name,
                "engineering_state": "draft",
                "is_plm": True,
                "company_id": company.id,
                "plm_share_scope": scope,
            }
        )

    # -- helpers ------------------------------------------------------------

    def _attach_as(self, user):
        """ir.attachment model scoped to `user` and their own companies only."""
        return (
            self.env["ir.attachment"]
            .with_user(user)
            .with_context(allowed_company_ids=user.company_ids.ids)
        )

    def _can_read(self, user, doc):
        """True if `doc` is visible to `user` via search (silent record-rule filter)."""
        return bool(self._attach_as(user).search([("id", "=", doc.id)]))

    # -- Rule 1: no PLM group -> never sees is_plm ---------------------------

    def test_rule1_non_plm_user_cannot_see_plm_documents(self):
        # Non-PLM documents remain fully visible.
        self.assertTrue(
            self._can_read(self.user_none, self.doc_nonplm),
            "A plain user must still see ordinary (non-PLM) attachments.",
        )
        # Every is_plm document is invisible, regardless of company or share scope.
        self.assertFalse(
            self._can_read(self.user_none, self.doc_a_own),
            "A user in no PLM group must not see an is_plm document (own company).",
        )
        self.assertFalse(
            self._can_read(self.user_none, self.doc_b_own),
            "A user in no PLM group must not see an is_plm document (other company).",
        )
        self.assertFalse(
            self._can_read(self.user_none, self.doc_b_all),
            "Even plm_share_scope='all' must not leak to a user in no PLM group.",
        )

    def test_rule1_non_plm_user_direct_read_denied(self):
        with self.assertRaises(ACCESS_DENIED):
            self.doc_a_own.with_user(self.user_none).read(["name"])

    # -- Rule 2: view user -> read-only, company scoped, no PLM menu ----------

    def test_rule2_view_user_reads_within_company(self):
        self.assertTrue(
            self._can_read(self.user_view, self.doc_a_own),
            "View user must read is_plm documents of their own company.",
        )
        self.assertTrue(
            self._can_read(self.user_view, self.doc_b_all),
            "View user must read is_plm documents shared to all companies.",
        )

    def test_rule2_view_user_cannot_see_other_company(self):
        self.assertFalse(
            self._can_read(self.user_view, self.doc_b_own),
            "View user must NOT see a 'own'-scoped document of another company.",
        )

    def test_rule2_view_user_cannot_write(self):
        with self.assertRaises(ACCESS_DENIED):
            self._attach_as(self.user_view).browse(self.doc_a_own.id).write(
                {"name": "hacked_by_view"}
            )

    def test_rule2_view_user_has_no_plm_menu(self):
        menu = self.env.ref("plm.plm_menu")
        view_group = self.env.ref("plm.group_plm_view_user")
        integration_group = self.env.ref("plm.group_plm_integration_user")
        admin_group = self.env.ref("plm.group_plm_admin")
        # The PLM application menu is not granted to the view group ...
        self.assertNotIn(
            view_group,
            menu.groups_id,
            "View users must not have the PLM application menu.",
        )
        # ... but is granted to integration and admin.
        self.assertIn(integration_group, menu.groups_id)
        self.assertIn(admin_group, menu.groups_id)
        # Behavioural check: the menu is filtered out for the view user.
        self.assertFalse(
            self.env["ir.ui.menu"].with_user(self.user_view).search([("id", "=", menu.id)])
        )
        self.assertTrue(
            self.env["ir.ui.menu"]
            .with_user(self.user_integration)
            .search([("id", "=", menu.id)])
        )

    # -- Rule 3: integration user -> read/write/create, company scoped, no delete

    def test_rule3_integration_reads_and_writes_within_company(self):
        self.assertTrue(self._can_read(self.user_integration, self.doc_a_own))
        self._attach_as(self.user_integration).browse(self.doc_a_own.id).write(
            {"name": "written_by_integration"}
        )
        self.doc_a_own.invalidate_recordset(["name"])
        self.assertEqual(self.doc_a_own.name, "written_by_integration")

    def test_rule3_integration_can_create_plm_document(self):
        new_doc = self._attach_as(self.user_integration).create(
            {
                "name": "created_by_integration",
                "datas": DUMMY_CONTENT,
                "res_model": "ir.attachment",
                "res_id": 0,
                "document_type": "3d",
                "engineering_code": "EC_created_by_integration",
                "engineering_state": "draft",
                "is_plm": True,
                "company_id": self.company_a.id,
                "plm_share_scope": "own",
            }
        )
        self.assertTrue(new_doc.exists())

    def test_rule3_integration_cannot_touch_other_company(self):
        # Not visible ...
        self.assertFalse(self._can_read(self.user_integration, self.doc_b_own))
        # ... and cannot be written.
        with self.assertRaises(ACCESS_DENIED):
            self._attach_as(self.user_integration).browse(self.doc_b_own.id).write(
                {"name": "cross_company_write"}
            )

    def test_rule3_integration_cannot_delete(self):
        with self.assertRaises(ACCESS_DENIED):
            self._attach_as(self.user_integration).browse(self.doc_a_own.id).unlink()
        # The document is still there.
        self.assertTrue(self.doc_a_own.exists())

    # -- Rule 4: admin -> full access, company rule ignored ------------------

    def test_rule4_admin_sees_all_companies(self):
        # Admin belongs to company_a only, yet sees every is_plm document.
        self.assertTrue(self._can_read(self.user_admin, self.doc_a_own))
        self.assertTrue(
            self._can_read(self.user_admin, self.doc_b_own),
            "Admin must see 'own'-scoped documents of other companies (company rule bypassed).",
        )
        self.assertTrue(self._can_read(self.user_admin, self.doc_b_all))

    def test_rule4_admin_writes_across_companies(self):
        self._attach_as(self.user_admin).browse(self.doc_b_own.id).write(
            {"name": "written_by_admin"}
        )
        self.doc_b_own.invalidate_recordset(["name"])
        self.assertEqual(self.doc_b_own.name, "written_by_admin")

    def test_rule4_admin_can_delete(self):
        doc = self._plm_doc("doc_admin_delete", self.company_b, "own")
        self._attach_as(self.user_admin).browse(doc.id).unlink()
        self.assertFalse(doc.exists())
