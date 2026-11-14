from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("-standard", "odoo_plm", "odoo_plm_cad_version")
class PlmCadVersion(TransactionCase):

    def setUp(self):
        super().setUp()
        self.inventor = self.env.ref("plm.plm_cad_inventor")
        self.solidworks = self.env.ref("plm.plm_cad_solidworks")

    def test_the_cads_come_with_their_versions(self):
        self.assertEqual(self.inventor.code, "INVENTOR")
        self.assertEqual(self.inventor.prog_id, "Inventor.Application")
        self.assertIn("2027", self.inventor.version_ids.mapped("name"))
        self.assertIn("2020", self.solidworks.version_ids.mapped("name"))
        # the newest first
        self.assertEqual(self.inventor.version_ids[0].name, "2027")
        self.assertEqual(self.env.ref("plm.plm_cad_version_inventor_2025").display_name, "Inventor 2025")
        # no target until somebody chooses it
        self.assertFalse(self.inventor.target_version_id)

    def test_the_target_version_by_cad_name(self):
        self.inventor.target_version_id = self.env.ref("plm.plm_cad_version_inventor_2027")
        cad = self.env["plm.cad"]
        # the documents write INVENTOR, the conversion rules Inventor
        self.assertEqual(cad.get_target_version("INVENTOR"), "2027")
        self.assertEqual(cad.get_target_version("Inventor"), "2027")
        self.assertEqual(cad.get_target_version(" inventor "), "2027")
        self.assertFalse(cad.get_target_version("SolidWorks"))
        self.assertFalse(cad.get_target_version("NoSuchCad"))
        self.assertFalse(cad.get_target_version(""))

    def test_the_target_is_a_version_of_its_cad(self):
        with self.assertRaises(ValidationError):
            self.inventor.target_version_id = self.env.ref("plm.plm_cad_version_solidworks_2025")

    def test_a_version_once_per_cad(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.env["plm.cad.version"].create({"cad_id": self.inventor.id, "name": "2025"})
            self.env.flush_all()
