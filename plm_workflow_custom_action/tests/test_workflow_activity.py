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
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_workflow_custom_action
#

SUMMARY = "Workflow custom action test activity"


@tagged("-standard", "odoo_plm_workflow_custom_action")
class PlmWorkflowActivity(TransactionCase, PlmEntityCreator):
    """A workflow custom action runs on the product that moves, also when the
    move comes from confirming its parent assembly, whatever records the
    context of the caller names in active_ids."""

    def setUp(self):
        super().setUp()
        self.parent = self.create_product_product("wf_activity_parent")
        self.child = self.create_product_product("wf_activity_child")
        self.bom = self.create_bom(self.parent, self.child)
        self.server_action = self.env["ir.actions.server"].create(
            {
                "name": "Workflow activity test",
                "model_id": self.env["ir.model"]._get_id("product.product"),
                "state": "next_activity",
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "activity_summary": SUMMARY,
                "activity_user_type": "specific",
                "activity_user_id": self.env.user.id,
            }
        )

    def _add_rule(self, before_after):
        self.env["plm.automatedwfaction"].create(
            {
                "name": "Workflow activity test",
                "apply_to": "product.product",
                "from_state": "draft",
                "to_state": "confirmed",
                "before_after": before_after,
                "child_ids": [(6, 0, self.server_action.ids)],
            }
        )

    def _activity_count(self, product):
        return self.env["mail.activity"].search_count(
            [
                ("res_model", "=", "product.product"),
                ("res_id", "=", product.id),
                ("summary", "=", SUMMARY),
            ]
        )

    def _check_confirm(self, product, context, before_after):
        self._add_rule(before_after)
        product.with_context(**context).action_confirm()
        self.assertEqual(self.child.engineering_state, "confirmed")
        self.assertEqual(self._activity_count(self.child), 1)
        self.assertEqual(self._activity_count(self.parent), int(product == self.parent))

    def _child_context(self):
        """Confirmed from its own form."""
        return {
            "active_model": "product.product",
            "active_id": self.child.id,
            "active_ids": self.child.ids,
        }

    def _parent_context(self):
        """The form button of the parent puts the parent in active_ids."""
        return {
            "active_model": "product.product",
            "active_id": self.parent.id,
            "active_ids": self.parent.ids,
        }

    def _other_record_context(self):
        """A form opened from another record keeps that record in active_ids."""
        return {
            "active_model": "mrp.bom",
            "active_id": self.bom.id,
            "active_ids": self.bom.ids,
        }

    def test_confirm_child_before(self):
        self._check_confirm(self.child, self._child_context(), "before")

    def test_confirm_child_after(self):
        self._check_confirm(self.child, self._child_context(), "after")

    def test_confirm_parent_from_its_form_before(self):
        self._check_confirm(self.parent, self._parent_context(), "before")

    def test_confirm_parent_from_its_form_after(self):
        self._check_confirm(self.parent, self._parent_context(), "after")

    def test_confirm_parent_from_another_record_before(self):
        self._check_confirm(self.parent, self._other_record_context(), "before")

    def test_confirm_parent_from_another_record_after(self):
        self._check_confirm(self.parent, self._other_record_context(), "after")

    def test_confirm_parent_without_active_ids_before(self):
        self._check_confirm(self.parent, {}, "before")

    def test_confirm_parent_without_active_ids_after(self):
        self._check_confirm(self.parent, {}, "after")
