# -*- coding: utf-8 -*-
"""The conversion rules are made in Odoo: a Plm Convert Admin creates and
deletes them, adds those of a template to a server; a rule cannot be both a
conversion and a CAD version update; the Massive Update names the two CAD
version updates of one format."""
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase, new_test_user

#
# --test-tags=plm_automated_convertion_format_admin
#

BASE = "base.group_user,plm.group_plm_view_user,"
CONVERT_VIEW = "plm_automated_convertion.group_plm_convert_view"
CONVERT_ADMIN = "plm_automated_convertion.group_plm_convert_admin"


@tagged("-standard", "plm_automated_convertion_format_admin")
class TestConvertFormatAdmin(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = new_test_user(cls.env, "format_admin", groups=BASE + CONVERT_ADMIN)
        cls.viewer = new_test_user(cls.env, "format_viewer", groups=BASE + CONVERT_VIEW)
        cls.server = cls.env["plm.convert.servers"].create(
            {"name": "Agent FA", "cad_agent": True, "workstation_guid": "FA-GUID"}
        )
        cls.step = cls.env["plm.convert.format"].create(
            {"server_id": cls.server.id, "cad_name": "Inventor", "start_format": ".faipt",
             "end_format": ".step", "cad_export_mode": "model_state", "available": True}
        )
        cls.template = cls.env["plm.convert.template"].create(
            {"name": "FA parts", "line_ids": [
                (0, 0, {"start_format": ".faipt", "end_format": ".step", "cad_export_mode": "model_state"}),
                (0, 0, {"start_format": ".faipt", "end_format": ".dxf", "cad_export_mode": "flat_pattern"}),
                (0, 0, {"start_format": ".faipt", "end_format": ".igs"}),
            ]}
        )

    def _rule(self, user, **values):
        return self.env["plm.convert.format"].with_user(user).create(
            dict({"server_id": self.server.id, "cad_name": "Inventor", "start_format": ".faipt",
                  "end_format": ".igs", "cad_export_mode": "file", "available": True}, **values)
        )

    # ------------------------------------------------------------ rights

    def test_an_admin_creates_and_deletes_a_rule(self):
        rule = self._rule(self.admin)
        self.assertEqual(rule.server_id, self.server)
        rule.with_user(self.admin).unlink()
        self.assertFalse(rule.exists())

    def test_a_viewer_neither_creates_nor_deletes(self):
        with self.assertRaises(AccessError):
            self._rule(self.viewer)
        with self.assertRaises(AccessError):
            self.step.with_user(self.viewer).unlink()

    def test_an_admin_adds_a_rule_from_the_server_form(self):
        with Form(self.server.with_user(self.admin)) as form:
            with form.available_format.new() as line:
                line.start_format = ".faipt"
                line.end_format = ".igs"
                line.cad_name = "Inventor"
                line.cad_export_mode = "file"
                line.available = True
        self.assertIn(".igs", self.server.available_format.mapped("end_format"))

    def test_a_cad_agent_made_by_hand_needs_no_address(self):
        """A CAD agent server without GUID (made by hand or by a module, as
        the CAD Workstation of Nisbau) is saved from its form without the
        address of a push server."""
        agent = self.env["plm.convert.servers"].create({"name": "Hand agent FA", "cad_agent": True})
        with Form(agent.with_user(self.admin)) as form:
            with form.available_format.new() as line:
                line.start_format = ".faipt"
                line.end_format = ".faipt"
                line.cad_name = "Inventor"
                line.cad_version_update = True
                line.available = True
        self.assertTrue(agent.available_format.cad_version_update)
        self.assertFalse(agent.address)
        # a push server still needs its address
        push = self.env["plm.convert.servers"].create({"name": "Push FA"})
        with self.assertRaises(AssertionError):
            with Form(push.with_user(self.admin)) as form:
                form.timeout = 3

    # -------------------------------------------------------- constraint

    def test_a_conversion_is_not_a_cad_version_update(self):
        with self.assertRaises(ValidationError):
            self.step.cad_version_update = True
        with self.assertRaises(ValidationError):
            self._rule(self.admin, cad_version_update=True)

    def test_a_cad_version_update_without_export_mode(self):
        rule = self._rule(self.admin, end_format=".faipt", cad_export_mode=False, cad_version_update=True)
        self.assertTrue(rule.cad_version_update)

    # ---------------------------------------------------------- template

    def _add_from_template(self, user=None, cad_name=None):
        env = self.env(user=user) if user else self.env
        form = Form(env["plm.convert.servers.template.wizard"].with_context(default_server_id=self.server.id))
        form.template_id = self.template
        if cad_name is not None:
            form.cad_name = cad_name
        return form.save().action_add()

    def test_the_template_adds_the_missing_rules(self):
        made = self._add_from_template(self.admin, cad_name="Inventor")
        self.assertEqual(
            sorted((rule.end_format, rule.cad_export_mode) for rule in made),
            [(".dxf", "flat_pattern"), (".igs", "file")],
            "the STEP is already there; a line without export mode makes one file",
        )
        self.assertEqual(set(made.mapped("cad_name")), {"Inventor"})
        self.assertTrue(all(made.mapped("available")))
        self.assertFalse(self._add_from_template(self.admin, cad_name="Inventor"), "nothing made twice")

    def test_the_cad_comes_from_the_rules_of_the_server(self):
        made = self._add_from_template(self.admin)
        self.assertEqual(set(made.mapped("cad_name")), {"Inventor"})

    def test_a_rule_already_there_is_available_again(self):
        self.step.available = False
        self._add_from_template(self.admin, cad_name="Inventor")
        self.assertTrue(self.step.available)

    def test_only_an_admin_adds_from_a_template(self):
        with self.assertRaises(AccessError):
            self._add_from_template(self.viewer, cad_name="Inventor")

    # ------------------------------------------------------ Massive Update

    def test_the_massive_update_names_the_two_version_updates(self):
        formats = self.env["plm.convert.format"]
        first = formats.create(
            {"server_id": self.server.id, "cad_name": "Inventor", "start_format": ".faipt",
             "end_format": ".faipt", "cad_version_update": True, "available": True}
        )
        second = first.copy({"end_format": ".FAIPT"})
        wizard = self.env["plm.cad.version.queue.wizard"].create(
            {"operation_type": "CAD_VERSION", "convert_format_ids": [(6, 0, (first | second).ids)]}
        )
        with self.assertRaises(UserError) as error:
            wizard.action_queue()
        message = str(error.exception)
        self.assertIn("id %s" % first.id, message)
        self.assertIn("id %s" % second.id, message)
