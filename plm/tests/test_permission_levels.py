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
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

#
# --test-tags=odoo_plm_permission_levels
#


@tagged("-standard", "odoo_plm_permission_levels")
class PlmPermissionLevels(TransactionCase):
    """The four PLM levels, on documents, components, their templates and their
    bills of materials: readonly state, readonly, integration, admin."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.readonly_state = cls._user("plm_lvl_state", "plm.group_plm_readonly_released")
        cls.readonly = cls._user("plm_lvl_readonly", "plm.group_plm_view_user")
        cls.integration = cls._user("plm_lvl_integration", "plm.group_plm_integration_user")
        cls.other_integration = cls._user(
            "plm_lvl_integration2", "plm.group_plm_integration_user"
        )
        cls.admin = cls._user("plm_lvl_admin", "plm.group_plm_admin")

    @classmethod
    def _user(cls, login, group_xmlid):
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "group_ids": [
                    Command.set(
                        [cls.env.ref("base.group_user").id, cls.env.ref(group_xmlid).id]
                    )
                ],
            }
        )

    def _document(self, code, user=None, state="draft"):
        document = self.env["ir.attachment"].with_user(user or self.env.user).create(
            {
                "name": code,
                "engineering_code": code,
                "datas": DUMMY_CONTENT,
                "is_plm": True,
            }
        )
        if state != "draft":
            document.sudo().with_context(check=False).engineering_state = state
        return document

    def _component(self, code, user=None, state="draft"):
        template = self.env["product.template"].with_user(user or self.env.user).create(
            {"name": code, "engineering_code": code}
        )
        if state != "draft":
            template.sudo().engineering_state = state
        return template

    def _can_read(self, user, record):
        return bool(
            record.with_user(user).sudo(False).search([("id", "=", record.id)])
        )

    # level 1: readonly state

    def test_readonly_state_reads_released_only(self):
        draft = self._document("LVL-D1")
        released = self._document("LVL-R1", state="released")
        under_modify = self._document("LVL-U1", state="undermodify")
        obsoleted = self._document("LVL-O1", state="obsoleted")
        self.assertFalse(self._can_read(self.readonly_state, draft))
        self.assertTrue(self._can_read(self.readonly_state, released))
        self.assertTrue(self._can_read(self.readonly_state, under_modify))
        self.assertFalse(self._can_read(self.readonly_state, obsoleted))

    def test_readonly_state_reads_released_components(self):
        draft = self._component("LVL-C-D")
        released = self._component("LVL-C-R", state="released")
        self.assertFalse(self._can_read(self.readonly_state, draft))
        self.assertTrue(self._can_read(self.readonly_state, released))
        self.assertTrue(
            self._can_read(self.readonly_state, released.product_variant_id)
        )

    def test_readonly_state_writes_nothing(self):
        released = self._document("LVL-R2", state="released")
        with mute_logger("odoo.addons.base.models.ir_model"), self.assertRaises(AccessError):
            released.with_user(self.readonly_state).write({"desc_modify": "no"})
        with mute_logger("odoo.addons.base.models.ir_model"), self.assertRaises(AccessError):
            self._document("LVL-N1", user=self.readonly_state)

    def test_the_released_only_group_is_the_same_level(self):
        user = self._user("plm_lvl_released_doc", "plm.group_plm_release_document")
        draft = self._document("LVL-D3")
        released = self._document("LVL-R3", state="released")
        self.assertFalse(self._can_read(user, draft))
        self.assertTrue(self._can_read(user, released))

    # level 2: readonly

    def test_readonly_reads_every_state(self):
        draft = self._document("LVL-D4")
        released = self._document("LVL-R4", state="released")
        self.assertTrue(self._can_read(self.readonly, draft))
        self.assertTrue(self._can_read(self.readonly, released))
        self.assertTrue(self._can_read(self.readonly, self._component("LVL-C4")))

    def test_readonly_writes_nothing(self):
        draft = self._document("LVL-D5")
        with mute_logger("odoo.addons.base.models.ir_model"), self.assertRaises(AccessError):
            draft.with_user(self.readonly).write({"desc_modify": "no"})
        with mute_logger("odoo.addons.base.models.ir_model"), self.assertRaises(AccessError):
            self._document("LVL-N2", user=self.readonly)
        with mute_logger("odoo.addons.base.models.ir_model"), self.assertRaises(AccessError):
            draft.with_user(self.readonly).unlink()

    # level 3: integration

    def test_integration_creates_and_writes(self):
        document = self._document("LVL-I1", user=self.integration)
        document.with_user(self.integration).write({"desc_modify": "mine"})
        other = self._document("LVL-I2")
        other.with_user(self.integration).write({"desc_modify": "someone else's"})

    def test_integration_deletes_only_its_own_drafts(self):
        own_draft = self._document("LVL-I3", user=self.integration)
        own_released = self._document("LVL-I4", user=self.integration, state="released")
        someone_else = self._document("LVL-I5", user=self.other_integration)
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(AccessError):
            own_released.with_user(self.integration).unlink()
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(AccessError):
            someone_else.with_user(self.integration).unlink()
        own_draft.with_user(self.integration).unlink()
        self.assertFalse(own_draft.exists())

    def test_integration_deletes_only_its_own_draft_components(self):
        own_draft = self._component("LVL-I6", user=self.integration)
        someone_else = self._component("LVL-I7", user=self.other_integration)
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(AccessError):
            someone_else.with_user(self.integration).unlink()
        own_draft.with_user(self.integration).unlink()
        self.assertFalse(own_draft.exists())

    # the odooPLM context

    def test_the_cad_context_grants_nothing(self):
        """Reading used to run as the superuser when the call carried the
        odooPLM context, which the CAD client puts on every call."""
        private = self.env["ir.attachment"].with_user(self.other_integration).create(
            {"name": "payslip.pdf", "datas": DUMMY_CONTENT}
        )
        released = self._document("LVL-CAD1", user=self.integration, state="released")
        self.env.flush_all()
        for user in (self.readonly, self.integration):
            for context in ({}, {"odooPLM": True}):
                self.env.invalidate_all()
                record = (
                    self.env["ir.attachment"]
                    .with_user(user)
                    .with_context(**context)
                    .browse(private.id)
                )
                with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(
                    AccessError
                ):
                    record.read(["datas"])
        self.env.invalidate_all()
        readable = (
            self.env["ir.attachment"]
            .with_user(self.integration)
            .with_context(odooPLM=True)
            .browse(released.id)
        )
        self.assertEqual(readable.read(["name"])[0]["name"], "LVL-CAD1")

    def test_the_cad_context_does_not_open_another_node(self):
        group = self.env["res.groups"].create({"name": "PLM test node group"})
        node = self.env["plm.access"].create(
            {
                "name": "Another department",
                "parent_id": self.env.company.plm_access_id.id,
                "read_group_ids": [Command.set(group.ids)],
            }
        )
        document = self._document("LVL-CAD2")
        document.sudo().plm_access_id = node
        self.env.flush_all()
        self.env.invalidate_all()
        record = (
            self.env["ir.attachment"]
            .with_user(self.integration)
            .with_context(odooPLM=True)
            .browse(document.id)
        )
        with mute_logger("odoo.addons.base.models.ir_rule"), self.assertRaises(AccessError):
            record.read(["datas"])

    # level 4: admin

    def test_admin_deletes_anything(self):
        released = self._document("LVL-A1", user=self.integration, state="released")
        released.with_user(self.admin).unlink()
        self.assertFalse(released.exists())
        component = self._component("LVL-A2", user=self.integration, state="released")
        component.with_user(self.admin).unlink()
        self.assertFalse(component.exists())
