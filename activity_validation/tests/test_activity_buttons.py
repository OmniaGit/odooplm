import json

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

STATE_BUTTONS = [
    "action_in_progress",
    "action_to_draft",
    "action_to_exception",
    "action_to_cancel",
    "action_to_done",
]


@tagged("-standard", "odoo_plm_activity_buttons")
class TestActivityButtons(TransactionCase, PlmEntityCreator):
    """get_user_activities tells the CAD client which state buttons an activity
    allows: the ones its form shows (the invisible of each button)"""

    def setUp(self):
        super().setUp()
        product = self.create_product_product("activity_buttons")
        self.activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.env.ref("plm.mail_activity_plm_activity").id,
                "res_model_id": self.env["ir.model"]._get_id("product.product"),
                "res_id": product.id,
                "user_id": self.env.uid,
                "summary": "check the buttons",
            }
        )

    def _allowed_buttons(self):
        _headers, lines = json.loads(
            self.env["product.product"].get_user_activities([self.activity.id])
        )
        self.assertEqual(len(lines), 1)
        return {name for name in STATE_BUTTONS if not lines[0][name]}

    def test_draft(self):
        self.activity.plm_state = "draft"
        self.assertEqual(
            self._allowed_buttons(), {"action_in_progress", "action_to_cancel"}
        )

    def test_in_progress(self):
        self.activity.plm_state = "in_progress"
        self.assertEqual(
            self._allowed_buttons(),
            {
                "action_to_draft",
                "action_to_exception",
                "action_to_cancel",
                "action_to_done",
            },
        )

    def test_exception_with_parent(self):
        """Progress is in the form twice: from exception only with a parent ECR"""
        self.activity.write({"plm_state": "exception", "has_parent": False})
        self.assertNotIn("action_in_progress", self._allowed_buttons())
        self.activity.write({"has_parent": True})
        self.assertIn("action_in_progress", self._allowed_buttons())
