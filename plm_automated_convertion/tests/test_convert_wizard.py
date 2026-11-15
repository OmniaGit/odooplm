"""The conversion command of the documents: the conversions of Odoo and of
the CAD workstations, the CAD version update and the templates."""
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("-standard", "plm_automated_convertion_wizard")
class TestConvertWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        servers = cls.env["plm.convert.servers"]
        formats = cls.env["plm.convert.format"]
        cls.odoo_server = servers.create({"name": "Odoo itself", "is_internal": True})
        cls.agent_server = servers.create({"name": "Hand made agent", "cad_agent": True})
        cls.stl = formats.create(
            {"server_id": cls.odoo_server.id, "cad_name": "Odoo", "start_format": ".wizprt",
             "end_format": ".stl", "available": True}
        )
        cls.step = formats.create(
            {"server_id": cls.agent_server.id, "cad_name": "Inventor", "start_format": ".wizprt",
             "end_format": ".step", "cad_export_mode": "model_state", "available": True}
        )
        cls.update = formats.create(
            {"server_id": cls.agent_server.id, "cad_name": "Inventor", "start_format": ".wizprt",
             "end_format": ".wizprt", "cad_version_update": True, "available": True}
        )
        # a workstation presenting the same STEP and a flat pattern
        servers.register_workstation(
            {"guid": "GUID-WIZARD", "hostname": "WS-WIZARD", "cads": [{"name": "Inventor"}],
             "features": ["CONVERT", "CAD_VERSION"],
             "conversions": [
                 {"cad": "Inventor", "start_format": ".wizprt", "end_format": ".step", "export_mode": "model_state"},
                 {"cad": "Inventor", "start_format": ".wizprt", "end_format": ".dxf", "export_mode": "flat_pattern"},
             ]}
        )
        cad = cls.env["plm.cad"].find_cad("Inventor") or cls.env["plm.cad"].create({"name": "Inventor"})
        version = cls.env["plm.cad.version"].create({"cad_id": cad.id, "name": "2099"})
        cad.target_version_id = version
        cls.user = new_test_user(
            cls.env, "wizard_designer", groups="base.group_user,plm.group_plm_view_user,plm_automated_convertion.group_plm_convert_view"
        )
        cls.other = new_test_user(
            cls.env, "wizard_other", groups="base.group_user,plm.group_plm_view_user,plm_automated_convertion.group_plm_convert_view"
        )
        cls.part = cls.env["ir.attachment"].create(
            {"name": "bracket.wizprt", "raw": b"part", "is_plm": True, "engineering_code": "WIZ-BRACKET"}
        )
        cls.template = cls.env["plm.convert.template"].create(
            {"name": "Sheet metal", "line_ids": [(0, 0, {"start_format": "WIZPRT", "end_format": "dxf"})]}
        )

    def wizard(self, user=None):
        env = self.env(user=user) if user else self.env
        return Form(
            env["plm.convert"].with_context(active_model="ir.attachment", active_ids=self.part.ids)
        )

    def offered(self, form):
        """(end format, made by) of the lines, in their order."""
        out = []
        for index in range(len(form.line_ids)):
            with form.line_ids.edit(index) as line:
                out.append((line.end_format, line.maker))
        return out

    def choose(self, form, end_format):
        with form.line_ids.edit([end for end, _maker in self.offered(form)].index(end_format)) as line:
            line.selected = True

    def chosen(self, form):
        out = []
        for index in range(len(form.line_ids)):
            with form.line_ids.edit(index) as line:
                if line.selected:
                    out.append(line.end_format)
        return out

    def test_each_conversion_once(self):
        form = self.wizard()
        # the STEP of the hand made rule and of the workstation is one line; no CAD version update line
        self.assertEqual(
            sorted(self.offered(form)),
            [(".dxf", "workstation"), (".step", "workstation"), (".stl", "odoo")],
        )
        self.assertTrue(form.cad_version_available)

    def test_a_workstation_conversion_is_queued_for_the_user(self):
        form = self.wizard(self.user)
        self.choose(form, ".step")
        wizard = form.save()
        action = wizard.action_convert()
        rows = self.env["plm.convert.stack"].search(action["domain"])
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows.operation_type, rows.cad_agent_state), ("CONVERT", "to_do"))
        self.assertEqual(rows.convrsion_rule, self.step)  # the rule made by hand, not the presented one
        self.assertEqual(rows.requester_id, self.user)
        with self.assertRaises(UserError):  # the same job is already waiting
            wizard.action_convert()

    def test_the_cad_version_update_of_one_file(self):
        form = self.wizard()
        form.cad_version_update = True
        rows = self.env["plm.convert.stack"].search(form.save().action_convert()["domain"])
        self.assertEqual((rows.operation_type, rows.cad_version_target), ("CAD_VERSION", "2099"))

    def test_a_template_chooses_its_conversions(self):
        form = self.wizard()
        form.template_id = self.template
        self.assertEqual(self.chosen(form), [".dxf"])

    def test_save_as_my_template(self):
        form = self.wizard(self.user)
        self.choose(form, ".stl")
        form.cad_version_update = True
        form.template_name = "My STL"
        wizard = form.save()
        wizard.action_save_template()
        mine = wizard.template_id
        self.assertEqual((mine.owner_id, mine.cad_version_update), (self.user, True))
        self.assertEqual(mine.line_ids.mapped("end_format"), [".stl"])
        templates = self.env["plm.convert.template"].with_user(self.other)
        self.assertNotIn(mine, templates.search([]))
        self.assertIn(self.template, templates.search([]))  # the predefined ones are for everybody
        with self.assertRaises(AccessError):
            self.template.with_user(self.other).name = "Changed"

    def test_nothing_chosen(self):
        with self.assertRaises(UserError):
            self.wizard().save().action_convert()
