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
import importlib.util

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo.tools.misc import file_path

from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

#
# --test-tags=odoo_plm_multicompany
#


@tagged("-standard", "odoo_plm_multicompany")
class PlmMultiCompanyAccess(TransactionCase):
    """PLM documents live in plm.access nodes: a tree per company, whose nodes
    name the groups that may read, write, create and delete their documents, or
    inherit them from the parent."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "PLM company B"})
        cls.root_a = cls.company_a.plm_access_id
        cls.root_b = cls.company_b.plm_access_id
        cls.group_rd = cls.env["res.groups"].create({"name": "PLM test R&D"})
        cls.group_purchase = cls.env["res.groups"].create({"name": "PLM test Purchase"})
        Access = cls.env["plm.access"]
        cls.rd = Access.create(
            {
                "name": "R&D",
                "parent_id": cls.root_a.id,
                "read_group_ids": [Command.set(cls.group_rd.ids)],
                "write_group_ids": [Command.set(cls.group_rd.ids)],
                "create_group_ids": [Command.set(cls.group_rd.ids)],
                "unlink_group_ids": [Command.set(cls.group_rd.ids)],
            }
        )
        cls.rd_prototypes = Access.create({"name": "Prototypes", "parent_id": cls.rd.id})
        cls.rd_for_suppliers = Access.create(
            {
                "name": "For suppliers",
                "parent_id": cls.rd.id,
                "read_group_ids": [Command.set(cls.group_purchase.ids)],
            }
        )
        plm_user = cls.env.ref("plm.group_plm_integration_user")
        cls.user_a = cls._user("plm_access_a", cls.company_a, plm_user)
        cls.user_a_rd = cls._user("plm_access_a_rd", cls.company_a, plm_user | cls.group_rd)
        cls.user_b = cls._user("plm_access_b", cls.company_b, plm_user)
        cls.user_not_plm = cls._user("plm_access_not_plm", cls.company_a)
        cls.plm_admin = cls._user(
            "plm_access_admin", cls.company_a, cls.env.ref("plm.group_plm_admin")
        )

    @classmethod
    def _user(cls, login, company, groups=None):
        groups = cls.env.ref("base.group_user") | (groups or cls.env["res.groups"])
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "company_id": company.id,
                "company_ids": [Command.set(company.ids)],
                "group_ids": [Command.set(groups.ids)],
            }
        )

    def _document(self, code, node, env=None, **values):
        return (env or self.env)["ir.attachment"].create(
            {
                "name": code,
                "engineering_code": code,
                "datas": DUMMY_CONTENT,
                "is_plm": True,
                "plm_access_id": node.id,
                **values,
            }
        )

    def _can_read(self, user, document):
        return bool(
            self.env["ir.attachment"].with_user(user).search([("id", "=", document.id)])
        )

    # the tree

    def test_every_company_has_its_root(self):
        self.assertEqual(self.root_a, self.env.ref("plm.plm_basic_access_model"))
        self.assertEqual(self.root_b.company_id, self.company_b)
        self.assertFalse(self.root_b.parent_id)
        self.assertEqual(self.rd_prototypes.company_id, self.company_a)
        self.assertEqual(
            self.rd_prototypes.complete_name, "%s / R&D / Prototypes" % self.root_a.name
        )

    def test_groups_are_inherited_until_redefined(self):
        self.assertFalse(self.root_a.effective_read_group_ids)
        self.assertEqual(self.rd_prototypes.effective_read_group_ids, self.group_rd)
        self.assertEqual(self.rd_for_suppliers.effective_read_group_ids, self.group_purchase)
        self.assertEqual(self.rd_for_suppliers.effective_write_group_ids, self.group_rd)
        self.rd.read_group_ids = [Command.set(self.group_purchase.ids)]
        self.assertEqual(self.rd_prototypes.effective_read_group_ids, self.group_purchase)

    def test_one_root_per_company(self):
        with self.assertRaises(ValidationError):
            self.env["plm.access"].create(
                {"name": "Second root", "company_id": self.company_a.id}
            )

    def test_only_the_plm_administrator_changes_nodes(self):
        """Even a node restricted to a department: the write groups say who
        writes its documents, not who manages the tree."""
        with self.assertRaises(UserError):
            self.rd.with_user(self.user_a_rd).write({"name": "Renamed"})
        self.rd.with_user(self.plm_admin).write({"name": "Renamed"})
        self.assertEqual(self.rd.name, "Renamed")

    def test_a_root_cannot_be_deleted(self):
        with self.assertRaises(UserError):
            self.root_b.unlink()

    def test_a_node_with_documents_stays_in_its_company(self):
        self._document("ACC-MOVE", self.rd_prototypes)
        with self.assertRaises(UserError):
            self.rd.write({"parent_id": self.root_b.id})

    # reading

    def test_companies_do_not_see_each_other(self):
        document = self._document("ACC-A", self.root_a)
        self.assertEqual(document.company_id, self.company_a)
        self.assertTrue(self._can_read(self.user_a, document))
        self.assertFalse(self._can_read(self.user_b, document))
        with self.assertRaises(AccessError):
            document.with_user(self.user_b).read(["name"])

    def test_a_department_hides_its_documents(self):
        document = self._document("ACC-RD", self.rd_prototypes)
        self.assertFalse(self._can_read(self.user_a, document))
        self.assertTrue(self._can_read(self.user_a_rd, document))

    def test_a_redefined_node_opens_to_its_own_groups(self):
        document = self._document("ACC-SUP", self.rd_for_suppliers)
        self.assertFalse(self._can_read(self.user_a_rd, document))
        self.user_a.group_ids = [Command.link(self.group_purchase.id)]
        self.assertTrue(self._can_read(self.user_a, document))

    def test_users_outside_plm_see_no_plm_document(self):
        document = self._document("ACC-NOPLM", self.root_a)
        self.assertFalse(self._can_read(self.user_not_plm, document))
        attachment = self.env["ir.attachment"].with_user(self.user_not_plm).create(
            {"name": "not a plm document", "datas": DUMMY_CONTENT}
        )
        self.assertTrue(self._can_read(self.user_not_plm, attachment))
        attachment.with_user(self.user_not_plm).unlink()

    # writing, creating, deleting

    def test_write_follows_the_node(self):
        node = self.env["plm.access"].create(
            {
                "name": "Read by all, written by R&D",
                "parent_id": self.root_a.id,
                "write_group_ids": [Command.set(self.group_rd.ids)],
            }
        )
        document = self._document("ACC-W", node)
        self.assertTrue(self._can_read(self.user_a, document))
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(AccessError):
            document.with_user(self.user_a).write({"desc_modify": "not allowed"})
        document.with_user(self.user_a_rd).write({"desc_modify": "allowed"})

    def test_create_follows_the_node(self):
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(AccessError):
            self._document("ACC-C1", self.rd_prototypes, env=self.env(user=self.user_a))
        self._document("ACC-C2", self.rd_prototypes, env=self.env(user=self.user_a_rd))

    def test_unlink_follows_the_node(self):
        node = self.env["plm.access"].create(
            {
                "name": "Delete by admins only",
                "parent_id": self.root_a.id,
                "unlink_group_ids": [Command.set(self.env.ref("plm.group_plm_admin").ids)],
            }
        )
        document = self._document("ACC-U", node)
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(AccessError):
            document.with_user(self.user_a).unlink()

    # where a new document goes

    def test_new_document_goes_to_the_company_root(self):
        Attachment = self.env["ir.attachment"].with_user(self.user_b)
        self.assertEqual(Attachment._get_plm_access_for("ACC-NEW"), self.root_b)

    def test_new_document_goes_to_the_user_default_node(self):
        self.user_a_rd.plm_access_id = self.rd_prototypes
        Attachment = self.env["ir.attachment"].with_user(self.user_a_rd)
        self.assertEqual(Attachment._get_plm_access_for("ACC-NEW"), self.rd_prototypes)

    def test_a_new_revision_joins_the_previous_ones(self):
        self._document("ACC-REV", self.rd_prototypes)
        Attachment = self.env["ir.attachment"].with_user(self.user_b)
        self.assertEqual(Attachment._get_plm_access_for("ACC-REV"), self.rd_prototypes)

    def test_cad_client_create_uses_the_node(self):
        self.user_a_rd.plm_access_id = self.rd_prototypes
        document = (
            self.env["ir.attachment"]
            .with_user(self.user_a_rd)
            .with_context(odooPLM=True)
            .create(
                {
                    "name": "ACC-CAD",
                    "engineering_code": "ACC-CAD",
                    "datas": DUMMY_CONTENT,
                    "document_type": "other",
                }
            )
        )
        self.assertEqual(document.plm_access_id, self.rd_prototypes)
        self.assertEqual(
            (document.res_model, document.res_id), ("plm.access", self.rd_prototypes.id)
        )

    def test_plm_document_created_without_node_gets_one(self):
        """A module creating a PLM document by hand, as the file conversions do,
        and naming no node."""
        document = self.env["ir.attachment"].with_user(self.user_b).create(
            {
                "name": "ACC-CONV",
                "engineering_code": "ACC-CONV",
                "datas": DUMMY_CONTENT,
                "is_plm": True,
            }
        )
        self.assertEqual(document.plm_access_id, self.root_b)

    def test_revisions_share_the_node(self):
        self._document("ACC-SHARE", self.root_a).with_context(
            check=False
        ).engineering_state = "released"
        with self.assertRaises(ValidationError):
            self._document("ACC-SHARE", self.rd, engineering_revision=1)

    # moving a document

    def test_a_draft_document_moves(self):
        document = self._document("ACC-D", self.root_a)
        document.plm_access_id = self.rd
        self.assertEqual(document.res_id, self.rd.id)

    def test_a_confirmed_document_does_not_move(self):
        document = self._document("ACC-CONF", self.root_a)
        document.with_context(check=False).engineering_state = "confirmed"
        with self.assertRaises(UserError):
            document.plm_access_id = self.rd

    def test_a_document_with_components_does_not_move(self):
        document = self._document("ACC-COMP", self.root_a)
        product = self.env["product.product"].create({"name": "ACC-COMP"})
        document.linkedcomponents = product
        with self.assertRaises(UserError):
            document.plm_access_id = self.rd

    def test_a_document_is_not_more_visible_than_its_product(self):
        document = self._document("ACC-PROD", self.root_b)
        product = self.env["product.product"].create(
            {"name": "ACC-PROD", "company_id": self.company_a.id}
        )
        with self.assertRaises(ValidationError):
            document.linkedcomponents = product
        with self.assertRaises(ValidationError):
            product.linkeddocuments = document
        shared = self.env["product.product"].create({"name": "ACC-SHARED"})
        document.linkedcomponents = shared

    def test_the_hierarchy_view_loads(self):
        views = self.env["plm.access"].get_views([(False, "hierarchy"), (False, "list")])
        self.assertIn("hierarchy", views["views"])

    # the upgrade

    def test_upgrade_attaches_documents_left_with_res_id_zero(self):
        """A document attached to nothing carries res_id 0 as often as NULL, and
        the scripts before 19.0.1.0.31 looked for NULL alone. Those documents
        kept no node, and since read access is granted through the node they
        hang from, no company rule ever reached them."""
        document = self._document("ACC-ZERO", self.root_a)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_attachment SET res_model = NULL, res_id = 0,"
            " plm_access_id = NULL WHERE id = %s",
            (document.id,),
        )
        self.env.invalidate_all()
        self.assertFalse(document.plm_access_id)
        path = file_path("plm/upgrades/19.0.1.0.31/post-migrate.py")
        spec = importlib.util.spec_from_file_location("plm_post_migrate_31", path)
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        script.migrate(self.env.cr, "19.0.1.0.30")
        self.env.invalidate_all()
        self.assertEqual(document.plm_access_id, self.root_a)
