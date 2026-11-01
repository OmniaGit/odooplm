from odoo.exceptions import AccessError
from odoo.tests import Form
from odoo.tests.common import TransactionCase, new_test_user, tagged

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

WRITE_THE_RECORDS = "base.group_user,base.group_partner_manager,product.group_product_manager"
ACTIVITY_USER = "activity_validation.group_force_activity_validation_user"


@tagged("-standard", "odoo_plm_activity_access")
class TestActivityAccess(TransactionCase, PlmEntityCreator):
    """Scheduling and opening an activity works for every internal user. The lines
    of a Change Request are read by everybody and created by Activity User only"""

    def setUp(self):
        super().setUp()
        self.user = new_test_user(self.env, login="activity_plain", groups=WRITE_THE_RECORDS)
        self.activity_user = new_test_user(
            self.env,
            login="activity_user",
            groups="%s,%s" % (WRITE_THE_RECORDS, ACTIVITY_USER),
        )
        self.partner = self.env["res.partner"].create({"name": "activity access"})
        self.product = self.create_product_product("activity_access")
        self.todo = self.env.ref("mail.mail_activity_data_todo")
        self.plm_activity = self.env.ref("plm.mail_activity_plm_activity")
        self.change_request = self.env.ref(
            "activity_validation.mail_activity_change_request"
        )

    def _schedule_form(self, user, record):
        return Form(
            self.env["mail.activity.schedule"]
            .with_user(user)
            .with_context(
                active_model=record._name,
                active_id=record.id,
                active_ids=record.ids,
            )
        )

    def _schedule(self, user, record, activity_type):
        form = self._schedule_form(user, record)
        form.activity_type_id = activity_type
        form.save().action_schedule_activities()
        activity = self.env["mail.activity"].search(
            [("res_model", "=", record._name), ("res_id", "=", record.id)]
        )
        self.assertEqual(activity.activity_type_id, activity_type)

    def _set_change_request_users(self):
        self.change_request.activity_user_ids = self.env.ref("base.user_admin")
        self.env.invalidate_all()

    def test_schedule_on_a_partner(self):
        self._schedule(self.user, self.partner, self.todo)

    def test_schedule_on_a_product(self):
        self._schedule(self.user, self.product, self.todo)

    def test_schedule_a_plm_activity(self):
        self._schedule(self.user, self.product, self.plm_activity)

    def test_schedule_a_change_request_without_lines(self):
        self._schedule(self.user, self.product, self.change_request)

    def test_open_an_activity_form(self):
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.todo.id,
                "res_model_id": self.env["ir.model"]._get_id("res.partner"),
                "res_id": self.partner.id,
                "user_id": self.user.id,
            }
        )
        form = Form(activity.with_user(self.user))
        self.assertEqual(len(form.children_ids), 0)

    def test_lines_are_refused_without_the_group(self):
        self._set_change_request_users()
        form = self._schedule_form(self.user, self.product)
        with self.assertRaises(AccessError):
            form.activity_type_id = self.change_request

    def test_activity_user_creates_the_lines(self):
        self._set_change_request_users()
        form = self._schedule_form(self.activity_user, self.product)
        form.activity_type_id = self.change_request
        self.assertEqual(len(form.children_ids), 1)
        form.save().action_schedule_activities()
