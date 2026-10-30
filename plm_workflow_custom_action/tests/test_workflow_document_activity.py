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
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_workflow_custom_action
#

DOCUMENT_SUMMARY = "Workflow custom action document test activity"
PRODUCT_SUMMARY = "Workflow custom action product test activity"


@tagged("-standard", "odoo_plm_workflow_custom_action")
class PlmWorkflowDocumentActivity(TransactionCase, PlmEntityCreator):
    """A workflow custom action that applies to attachments runs on the document
    that moves: confirmed from its form, without active ids, or through the
    product it is linked to. An action that applies to products never runs on a
    document."""

    def setUp(self):
        super().setUp()
        self.document = self.create_document("wf_activity_document")
        self.document.is_plm = True
        self.product = self.create_product_product("wf_activity_product")
        self.product.linkeddocuments = [(4, self.document.id)]

    def _add_rule(self, apply_to, before_after, summary):
        server_action = self.env["ir.actions.server"].create(
            {
                "name": summary,
                "model_id": self.env["ir.model"]._get_id(apply_to),
                "state": "next_activity",
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "activity_summary": summary,
                "activity_user_type": "specific",
                "activity_user_id": self.env.user.id,
            }
        )
        self.env["plm.automatedwfaction"].create(
            {
                "name": summary,
                "apply_to": apply_to,
                "from_state": "draft",
                "to_state": "confirmed",
                "before_after": before_after,
                "child_ids": [(6, 0, server_action.ids)],
            }
        )

    def _activity_count(self, record, summary):
        return self.env["mail.activity"].search_count(
            [
                ("res_model", "=", record._name),
                ("res_id", "=", record.id),
                ("summary", "=", summary),
            ]
        )

    def _check_document_confirm(self, before_after, context):
        self._add_rule("ir.attachment", before_after, DOCUMENT_SUMMARY)
        self.document.with_context(**context).action_confirm()
        self.assertEqual(self.document.engineering_state, "confirmed")
        self.assertEqual(self._activity_count(self.document, DOCUMENT_SUMMARY), 1)

    def _document_context(self):
        """The form button of the document puts the document in active_ids."""
        return {
            "active_model": "ir.attachment",
            "active_id": self.document.id,
            "active_ids": self.document.ids,
        }

    def test_confirm_document_from_its_form_before(self):
        self._check_document_confirm("before", self._document_context())

    def test_confirm_document_from_its_form_after(self):
        self._check_document_confirm("after", self._document_context())

    def test_confirm_document_without_active_ids_before(self):
        self._check_document_confirm("before", {})

    def test_confirm_document_without_active_ids_after(self):
        self._check_document_confirm("after", {})

    def _check_product_confirm(self, before_after):
        """The product form button puts the product in active_ids."""
        self._add_rule("ir.attachment", before_after, DOCUMENT_SUMMARY)
        self.product.with_context(
            active_model="product.product",
            active_id=self.product.id,
            active_ids=self.product.ids,
        ).action_confirm()
        self.assertEqual(self.document.engineering_state, "confirmed")
        self.assertEqual(self._activity_count(self.document, DOCUMENT_SUMMARY), 1)
        self.assertEqual(self._activity_count(self.product, DOCUMENT_SUMMARY), 0)

    def test_confirm_document_through_its_product_before(self):
        self._check_product_confirm("before")

    def test_confirm_document_through_its_product_after(self):
        self._check_product_confirm("after")

    def _check_product_rule_skips_document(self, before_after):
        self._add_rule("product.product", before_after, PRODUCT_SUMMARY)
        self.document.with_context(**self._document_context()).action_confirm()
        self.assertEqual(self.document.engineering_state, "confirmed")
        self.assertEqual(self._activity_count(self.document, PRODUCT_SUMMARY), 0)

    def test_product_rule_skips_document_before(self):
        self._check_product_rule_skips_document("before")

    def test_product_rule_skips_document_after(self):
        self._check_product_rule_skips_document("after")
