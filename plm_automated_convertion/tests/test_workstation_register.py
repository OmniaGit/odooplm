import datetime
import json

from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase, new_test_user

PRESENTATION = {
    "guid": "Y89F7221F0AN",
    "hostname": "CAD-WS-01",
    "version": "2026.1.18",
    "work_hours": ["* 20-23,0-5 * * *"],
    "features": ["CAD_VERSION"],
    "cads": [
        {"name": "Inventor", "version": "2025", "prog_id": "Inventor.Application"},
        {"name": "SolidWorks", "version": "2025", "prog_id": "SldWorks.Application"},
    ],
    "conversions": [
        {"cad": "Inventor", "start_format": ".idw", "end_format": ".dwg", "export_mode": "file"},
        {"cad": "Inventor", "start_format": "ipt", "end_format": "STEP", "export_mode": "model_state"},
        {"cad": "Inventor", "start_format": ".ipt", "end_format": ".dxf", "export_mode": "flat_pattern"},
    ],
}


@tagged("-standard", "plm_automated_convertion_workstation")
class TestWorkstationRegister(TransactionCase):

    def register(self, **changes):
        return self.env["plm.convert.servers"].register_workstation(dict(PRESENTATION, **changes))

    def test_a_new_workstation_fills_the_list(self):
        answer = self.register()
        server = self.env["plm.convert.servers"].browse(answer["server_id"])
        self.assertEqual(answer, {"server_id": server.id, "name": "CAD-WS-01", "enabled": True})
        self.assertEqual(server.workstation_guid, "Y89F7221F0AN")
        self.assertEqual((server.hostname, server.agent_version), ("CAD-WS-01", "2026.1.18"))
        self.assertTrue(server.alive)
        self.assertFalse(server.is_internal)
        self.assertEqual(server.work_hours, "* 20-23,0-5 * * *")
        self.assertEqual(server.features, "CAD_VERSION")
        self.assertEqual(sorted(server.workstation_cad_ids.mapped("cad_name")), ["Inventor", "SolidWorks"])
        formats = server.available_format
        self.assertEqual(
            sorted((f.start_format, f.end_format, f.cad_export_mode, f.available, f.presented) for f in formats),
            [
                (".idw", ".dwg", "file", True, True),
                (".ipt", ".dxf", "flat_pattern", True, True),
                (".ipt", ".step", "model_state", True, True),
            ],
        )

    def test_the_queue_of_the_server(self):
        server = self.env["plm.convert.servers"].browse(self.register()["server_id"])
        other = self.env["plm.convert.servers"].browse(self.register(guid="OTHER", hostname="CAD-WS-02")["server_id"])
        document = self.env["ir.attachment"].create({"name": "part.ipt", "raw": b"x"})
        stack = self.env["plm.convert.stack"]
        mine = stack.create(
            [{"convrsion_rule": rule.id, "start_document_id": document.id, "operation_type": "CONVERT"}
             for rule in server.available_format]
        )
        stack.create({"convrsion_rule": other.available_format[0].id, "start_document_id": document.id,
                      "operation_type": "CONVERT"})
        self.assertEqual(server.stack_count, 3)
        action = server.action_view_stack()
        self.assertEqual(action["res_model"], "plm.convert.stack")
        self.assertEqual(stack.search(action["domain"]), mine)

    def test_the_same_guid_is_the_same_workstation(self):
        first = self.register()["server_id"]
        server = self.env["plm.convert.servers"].browse(first)
        server.write({"name": "Engineering workstation", "available": False})
        manual = self.env["plm.convert.format"].create(
            {"server_id": first, "start_format": ".iam", "end_format": ".stp", "cad_name": "Inventor",
             "available": True}
        )
        conversions = [c for c in PRESENTATION["conversions"] if c["end_format"] != ".dxf"]
        answer = self.register(version="2026.1.19", cads=PRESENTATION["cads"][:1], conversions=conversions)
        self.assertEqual(answer["server_id"], first)
        # the name and the switch set by hand stay
        self.assertEqual((answer["name"], answer["enabled"]), ("Engineering workstation", False))
        self.assertEqual(server.agent_version, "2026.1.19")
        self.assertEqual(server.workstation_cad_ids.mapped("cad_name"), ["Inventor"])
        dxf = server.available_format.filtered(lambda f: f.end_format == ".dxf")
        self.assertFalse(dxf.available, "a conversion no longer presented is unavailable")
        self.assertTrue(manual.available, "a format made by hand is not touched")
        self.assertEqual(len(server.available_format), 4, "no format made twice")

    def test_alive_only_after_a_recent_contact(self):
        server = self.env["plm.convert.servers"].browse(self.register()["server_id"])
        server.sudo().write({"last_contact": datetime.datetime.now() - datetime.timedelta(hours=1)})
        server.invalidate_recordset(["alive"])
        self.assertFalse(server.alive)

    def test_a_registration_needs_the_guid(self):
        with self.assertRaises(UserError):
            self.register(guid=" ")

    def test_bad_lines_are_left_out(self):
        server = self.env["plm.convert.servers"].browse(
            self.register(
                cads=[{"version": "2025"}, "x"],
                conversions=[{"cad": "Inventor", "start_format": ".ipt", "end_format": ".x", "export_mode": "weird"},
                             "x"],
            )["server_id"]
        )
        self.assertFalse(server.workstation_cad_ids)
        self.assertFalse(server.available_format)


@tagged("-standard", "plm_automated_convertion_workstation")
class TestWorkstationRegisterHttp(HttpCase):

    def setUp(self):
        super().setUp()
        new_test_user(self.env, login="cad_ws_admin", password="cad_ws_admin_pwd",
                      groups="base.group_user,plm_automated_convertion.group_plm_convert_admin")
        new_test_user(self.env, login="cad_ws_user", password="cad_ws_user_pwd", groups="base.group_user")

    def post(self, body):
        return self.url_open("/plm_cad_agent/register", data=body, headers={"Content-Type": "application/json"})

    def test_register(self):
        self.authenticate("cad_ws_admin", "cad_ws_admin_pwd")
        response = self.post(json.dumps(PRESENTATION))
        self.assertEqual(response.status_code, 200)
        answer = response.json()
        self.assertEqual(answer["name"], "CAD-WS-01")
        self.assertEqual(self.env["plm.convert.servers"].browse(answer["server_id"]).workstation_guid, "Y89F7221F0AN")

    def test_only_a_convert_admin(self):
        self.authenticate("cad_ws_user", "cad_ws_user_pwd")
        self.assertEqual(self.post(json.dumps(PRESENTATION)).status_code, 403)

    def test_errors(self):
        self.authenticate("cad_ws_admin", "cad_ws_admin_pwd")
        self.assertEqual(self.post("not json").status_code, 400)
        self.assertEqual(self.post(json.dumps({"hostname": "x"})).status_code, 400)

    def test_release(self):
        server = self.env["plm.convert.servers"].create({"name": "Release agent", "cad_agent": True})
        rule = self.env["plm.convert.format"].create(
            {"server_id": server.id, "cad_name": "Inventor", "start_format": ".relprt", "end_format": ".step",
             "cad_export_mode": "file", "available": True}
        )
        document = self.env["ir.attachment"].create({"name": "part.relprt", "raw": b"x"})
        row = self.env["plm.convert.stack"].create(
            {"convrsion_rule": rule.id, "start_document_id": document.id, "operation_type": "CONVERT",
             "cad_agent_state": "downloaded", "cad_hostname": "WS"}
        )
        self.authenticate("cad_ws_admin", "cad_ws_admin_pwd")
        response = self.url_open("/plm_cad_agent/release", data={"stack_ids": "%s,%s" % (row.id, row.id + 100000)})
        self.assertEqual(response.json(), {"released": [row.id]})
        row.invalidate_recordset()
        self.assertEqual((row.cad_agent_state, row.cad_hostname), ("to_do", False))
        self.assertEqual(self.url_open("/plm_cad_agent/release", data={"stack_ids": "x"}).status_code, 400)
