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
"""Changes, asked for through the MCP tools.

The one behaviour worth guarding here is who the answer is about.
plm_my_validations takes no user: it answers for whoever owns the key in use.
A version that accepted a name would let any key read anybody's queue, and that
is the kind of regression a reviewer would wave through as a convenience.

    odoo --test-tags=odoo_plm_mcp -i plm_mcp_ecr -d <database>
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator


@tagged("-standard", "odoo_plm_mcp")
class TestChangeRequests(TransactionCase, PlmEntityCreator):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool = cls.env["plm.mcp.tool"]
        cls.activity_type = cls.env.ref(
            "activity_validation.mail_activity_change_request")
        cls.other_user = cls.env["res.users"].create({
            "name": "Somebody else",
            "login": "mcp_ecr_other",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

    def setUp(self):
        super().setUp()
        self.part = self.create_product_product("Part", "MCPE-PRT-001")
        self.mine = self.request_on(self.part, self.env.user, "Mine to handle")
        self.theirs = self.request_on(self.part, self.other_user, "Not mine")

    def request_on(self, product, user, summary):
        return self.env["mail.activity"].create({
            "activity_type_id": self.activity_type.id,
            "res_model_id": self.env["ir.model"]._get("product.product").id,
            "res_id": product.id,
            "user_id": user.id,
            "summary": summary,
            "plm_state": "in_progress",
        })

    # ------------------------------------------------------------- open ones
    def test_open_changes_are_listed(self):
        changes = self.tool.plm_change_requests()
        summaries = [row["summary"] for row in changes["changes"]]
        self.assertIn("Mine to handle", summaries)
        self.assertIn("Not mine", summaries)

    def test_changes_can_be_asked_for_one_part(self):
        changes = self.tool.plm_change_requests(part="MCPE-PRT-001")
        self.assertGreaterEqual(changes["count"], 2)
        for row in changes["changes"]:
            self.assertEqual(row["part"]["engineering_code"], "MCPE-PRT-001")

    def test_a_part_with_no_changes_answers_empty(self):
        changes = self.tool.plm_change_requests(part="MCPE-NO-SUCH-CODE")
        self.assertEqual(changes["count"], 0)

    def test_the_answer_says_it_left_the_closed_ones_out(self):
        """Otherwise a count reads as "all changes" when it is "the open ones"."""
        changes = self.tool.plm_change_requests()
        self.assertTrue(changes["open_only"])

    def test_a_request_is_told_apart_from_an_order(self):
        self.mine.is_eco = True
        orders = self.tool.plm_change_requests(kind="order")
        self.assertIn("Mine to handle",
                      [row["summary"] for row in orders["changes"]])
        requests = self.tool.plm_change_requests(kind="request")
        self.assertNotIn("Mine to handle",
                         [row["summary"] for row in requests["changes"]])

    def test_the_part_travels_with_the_change(self):
        changes = self.tool.plm_change_requests(part="MCPE-PRT-001")
        row = changes["changes"][0]
        self.assertEqual(row["part"]["engineering_code"], "MCPE-PRT-001")
        self.assertIn("engineering_state", row["part"])

    # ------------------------------------------------------------ my queue
    def test_my_validations_answers_for_the_calling_user(self):
        mine = self.tool.plm_my_validations()
        summaries = [row["summary"] for row in mine["changes"]]
        self.assertIn("Mine to handle", summaries)
        self.assertNotIn("Not mine", summaries)

    def test_my_validations_follows_the_environment(self):
        """Change the user, change the answer — no argument involved."""
        as_other = self.tool.with_user(self.other_user).plm_my_validations()
        summaries = [row["summary"] for row in as_other["changes"]]
        self.assertIn("Not mine", summaries)
        self.assertNotIn("Mine to handle", summaries)
        self.assertEqual(as_other["user"], self.other_user.name)

    def test_my_validations_takes_no_user_argument(self):
        """The absence is the feature: it cannot be pointed at someone else."""
        spec = self.tool._tool_specs()["plm_my_validations"][1]
        self.assertNotIn("user", spec["inputSchema"]["properties"])
