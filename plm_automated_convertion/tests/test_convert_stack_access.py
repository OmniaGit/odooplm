# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

#
# --test-tags=plm_automated_convertion_access
#

PLM_USER = "base.group_user,plm.group_plm_integration_user"
CONVERT_VIEW = "plm_automated_convertion.group_plm_convert_view"


@tagged("-standard", "plm_automated_convertion_access")
class TestConvertStackAccess(TransactionCase):
    """Saving a STEP/DXF document queues its preview, whatever the rights of
    the user on the conversion stack (issue #111)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view_user = new_test_user(
            cls.env, login="convert_view_user", groups=PLM_USER + "," + CONVERT_VIEW
        )
        cls.plm_user = new_test_user(cls.env, login="convert_plm_user", groups=PLM_USER)

    def _create_step(self, user, name):
        return (
            self.env["ir.attachment"]
            .with_user(user)
            .create(
                {
                    "name": name,
                    "datas": base64.b64encode(b"ISO-10303-21;"),
                    "engineering_code": name,
                    "res_model": "ir.attachment",
                    "res_id": 0,
                }
            )
        )

    def _preview_stack(self, document):
        return (
            self.env["plm.convert.stack"]
            .sudo()
            .search(
                [
                    ("start_document_id", "=", document.id),
                    ("operation_type", "=", "UPDATE"),
                ]
            )
        )

    def _assert_preview_queued(self, document):
        stack = self._preview_stack(document)
        self.assertEqual(len(stack), 1)
        self.assertEqual(stack.sequence, stack.id)

    def test_convert_view_user_saves_a_step(self):
        document = self._create_step(self.view_user, "view_user_part.step")
        self._assert_preview_queued(document)

    def test_plm_user_without_convert_groups_saves_a_step(self):
        document = self._create_step(self.plm_user, "plm_user_part.step")
        self._assert_preview_queued(document)
        document.with_user(self.plm_user).write({"description": "changed"})
        self._assert_preview_queued(document)

    def test_convert_view_user_cannot_write_the_output_name_rule(self):
        document = self._create_step(self.view_user, "rule_write_part.step")
        stack = self._preview_stack(document)
        with self.assertRaises(AccessError) as refused:
            stack.with_user(self.view_user).write({"output_name_rule": "'x'"})
        self.assertIn("output name rule", str(refused.exception))

    def test_convert_view_user_creates_a_stack_without_output_name_rule(self):
        document = self._create_step(self.view_user, "rule_create_part.step")
        stack = (
            self.env["plm.convert.stack"]
            .with_user(self.view_user)
            .create(
                {
                    "operation_type": "CONVERT",
                    "start_document_id": document.id,
                    "convrsion_rule": self.env.ref(
                        "plm_automated_convertion.update_step_preview_png"
                    ).id,
                    "output_name_rule": "'x'",
                }
            )
        )
        self.assertFalse(stack.sudo().output_name_rule)
        self.assertEqual(stack.sudo().sequence, stack.id)
