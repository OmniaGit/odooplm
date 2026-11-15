"""Which jobs of the queue a registered CAD workstation takes: the ones it
can do (its CADs, the conversions it presented) and may take (the groups of
the user who asked for them)."""
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

HOSTPWS = "c:\\corebomweb\\work"


def presentation(guid, hostname, conversions, features=("CONVERT",), cads=("Inventor",)):
    return {
        "guid": guid,
        "hostname": hostname,
        "version": "2026.1.21",
        "features": list(features),
        "cads": [{"name": cad, "version": "2025"} for cad in cads],
        "conversions": [
            {"cad": "Inventor", "start_format": start, "end_format": end, "export_mode": mode}
            for start, end, mode in conversions
        ],
    }


@tagged("-standard", "plm_automated_convertion_dispatch")
class TestQueueDispatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        servers = cls.env["plm.convert.servers"]
        # the conversions of the jobs belong to a server made by hand
        cls.agent_server = servers.create({"name": "Agent server", "cad_agent": True, "is_internal": False})
        formats = cls.env["plm.convert.format"]
        cls.step = formats.create(
            {"server_id": cls.agent_server.id, "cad_name": "Inventor", "start_format": ".ipt",
             "end_format": ".step", "cad_export_mode": "model_state", "available": True}
        )
        cls.dxf = formats.create(
            {"server_id": cls.agent_server.id, "cad_name": "Inventor", "start_format": ".ipt",
             "end_format": ".dxf", "cad_export_mode": "flat_pattern", "available": True}
        )
        cls.update = formats.create(
            {"server_id": cls.agent_server.id, "cad_name": "Inventor", "start_format": ".ipt",
             "end_format": ".ipt", "cad_version_update": True, "available": True}
        )
        cls.engineering = cls.env["res.groups"].create({"name": "Engineering workstations"})
        cls.engineer = new_test_user(cls.env, "dispatch_engineer", groups="base.group_user")
        cls.engineer.groups_id = [(4, cls.engineering.id)]
        cls.designer = new_test_user(cls.env, "dispatch_designer", groups="base.group_user")
        register = servers.register_workstation
        cls.shared = servers.browse(
            register(presentation("GUID-SHARED", "WS-SHARED", [(".ipt", ".step", "model_state")]))["server_id"]
        )
        cls.tied = servers.browse(
            register(
                presentation(
                    "GUID-TIED", "WS-TIED",
                    [(".ipt", ".step", "model_state"), (".ipt", ".dxf", "flat_pattern")],
                    features=("CONVERT", "CAD_VERSION"),
                )
            )["server_id"]
        )
        cls.tied.group_ids = [(4, cls.engineering.id)]

    def job(self, rule, requester, name="part.ipt", operation="CONVERT"):
        document = self.env["ir.attachment"].create({"name": name, "raw": b"x"})
        return self.env["plm.convert.stack"].create(
            {"convrsion_rule": rule.id, "start_document_id": document.id, "operation_type": operation,
             "requester_id": requester.id}
        )

    def take(self, workstation, operation="CONVERT"):
        data = self.env["plm.convert.stack"].cad_agent_next_batch(
            workstation.hostname, HOSTPWS, 10, operation, guid=workstation.workstation_guid
        )
        return self.env["plm.convert.stack"].browse([row["stack_id"] for row in data["rows"]])

    def test_a_job_waits_for_the_state_to_do(self):
        job = self.job(self.step, self.designer)
        self.assertEqual(job.cad_agent_state, "to_do")
        self.assertEqual(self.env["plm.convert.stack"].create(
            {"convrsion_rule": self.step.id, "operation_type": "CONVERT"}).requester_id, self.env.user)

    def test_a_shared_workstation_takes_the_jobs_of_the_users_without_workstation(self):
        designer_job = self.job(self.step, self.designer)
        engineer_job = self.job(self.step, self.engineer)
        self.assertEqual(self.take(self.shared), designer_job)
        self.assertEqual(designer_job.workstation_id, self.shared)
        self.assertEqual(designer_job.cad_agent_state, "downloaded")
        self.assertEqual(engineer_job.cad_agent_state, "to_do")  # waits for the workstation of its group

    def test_a_tied_workstation_takes_only_the_jobs_of_its_groups(self):
        designer_job = self.job(self.step, self.designer)
        engineer_job = self.job(self.step, self.engineer)
        self.assertEqual(self.take(self.tied), engineer_job)
        self.assertEqual(designer_job.cad_agent_state, "to_do")
        self.assertIn(engineer_job, self.env["plm.convert.stack"].search(self.tied._stack_domain()))

    def test_the_jobs_of_a_tied_user_wait_when_his_workstation_is_off(self):
        engineer_job = self.job(self.step, self.engineer)
        self.tied.available = False
        data = self.env["plm.convert.stack"].cad_agent_next_batch(
            "WS-TIED", HOSTPWS, 10, "CONVERT", guid="GUID-TIED"
        )
        self.assertEqual(data["rows"], [])
        self.assertTrue(data["message"])
        self.assertFalse(self.take(self.shared))
        self.assertEqual(engineer_job.cad_agent_state, "to_do")

    def test_only_the_conversions_the_workstation_presented(self):
        dxf_job = self.job(self.dxf, self.designer)
        self.assertFalse(self.take(self.shared))  # it presented the STEP only
        self.engineering.users = [(4, self.designer.id)]
        self.assertEqual(self.take(self.tied), dxf_job)

    def test_a_cad_version_update_needs_the_function(self):
        update_job = self.job(self.update, self.engineer, operation="CAD_VERSION")
        self.engineering.users = [(3, self.engineer.id)]  # no more tied: the shared one could take it
        self.assertFalse(self.take(self.shared, "CAD_VERSION"))  # no CAD_VERSION presented
        self.tied.group_ids = [(5, 0, 0)]
        self.assertEqual(self.take(self.tied, "CAD_VERSION"), update_job)

    def test_an_unknown_workstation_registers_first(self):
        with self.assertRaises(UserError):
            self.env["plm.convert.stack"].cad_agent_next_batch("WS-X", HOSTPWS, 10, "CONVERT", guid="GUID-X")

    def test_without_guid_as_before(self):
        engineer_job = self.job(self.step, self.engineer)
        data = self.env["plm.convert.stack"].cad_agent_next_batch("WS-OLD", HOSTPWS, 10, "CONVERT", "Inventor")
        self.assertEqual([row["stack_id"] for row in data["rows"]], engineer_job.ids)
        self.assertFalse(engineer_job.workstation_id)

    def test_the_jobs_odoo_converts_have_the_same_state(self):
        internal = self.env["plm.convert.servers"].create({"name": "Odoo", "is_internal": True})
        rule = self.env["plm.convert.format"].create(
            {"server_id": internal.id, "cad_name": "Odoo", "start_format": ".step", "end_format": ".stl", "available": True}
        )
        job = self.job(rule, self.designer, name="part.step")
        job.setToConverted()
        self.assertEqual((job.conversion_done, job.cad_agent_state), (True, "done"))
        job.setToConver()
        self.assertEqual((job.conversion_done, job.cad_agent_state), (False, "to_do"))
