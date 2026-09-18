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
import psycopg2

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

#
# --test-tags=odoo_plm_multicompany
#


@tagged("-standard", "odoo_plm_multicompany")
class PlmMultiCompanyCode(TransactionCase):
    """An engineering code is unique in the whole database: two companies cannot
    create the same one, even when neither can see the other's records.

    The company of a revision is not covered here: 18.0 has no constraint tying
    the revisions of a code to one company, nor any guard on changing the
    company of a record that is past draft, carries a bill of materials or has
    documents. Those tests belong with the plm.access port.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "PLM company B"})
        cls.user_b = cls.env["res.users"].create(
            {
                "name": "PLM user B",
                "login": "plm_user_b",
                "company_id": cls.company_b.id,
                "company_ids": [Command.set(cls.company_b.ids)],
                "groups_id": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("plm.group_plm_integration_user").id,
                        ]
                    )
                ],
            }
        )

    def _template(self, code, revision=0, company=None, **values):
        return self.env["product.template"].create(
            {
                "name": code,
                "engineering_code": code,
                "engineering_revision": revision,
                "company_id": (company or self.company_a).id,
                **values,
            }
        )

    def test_user_of_another_company_cannot_reuse_a_code(self):
        self._template("MC-P100")
        template_b = self.env["product.template"].with_user(self.user_b)
        self.assertFalse(template_b.search([("engineering_code", "=", "MC-P100")]))
        with self.assertRaisesRegex(UserError, "already in use"):
            template_b.create({"name": "MC-P100", "engineering_code": "MC-P100"})
        with self.assertRaises(UserError):
            self.env["product.product"].with_user(self.user_b).create(
                {"name": "MC-P100", "engineering_code": "MC-P100"}
            )

    def test_the_message_does_not_name_the_company(self):
        self._template("MC-P101")
        try:
            self.env["product.template"].with_user(self.user_b).create(
                {"name": "MC-P101", "engineering_code": "MC-P101"}
            )
        except UserError as error:
            self.assertNotIn(self.company_a.name, str(error))
        else:
            self.fail("The code was created twice")

    def test_document_code_reused_gives_a_message(self):
        values = {
            "datas": DUMMY_CONTENT,
            "name": "MC-D100",
            "engineering_code": "MC-D100",
            "res_model": "ir.attachment",
            "res_id": 0,
            "document_type": "other",
        }
        self.env["ir.attachment"].create(values)
        with self.assertRaisesRegex(UserError, "already in use"):
            self.env["ir.attachment"].create(values)

    def test_unique_index_on_both_tables(self):
        for table in ("product_template", "ir_attachment"):
            self.env.cr.execute(
                "SELECT indexdef FROM pg_indexes WHERE indexname = %s",
                ("unique_index_%s" % table,),
            )
            (indexdef,) = self.env.cr.fetchone()
            self.assertIn("UNIQUE", indexdef)
            self.assertIn("(engineering_code IS NOT NULL)", indexdef)
            self.assertNotIn("OR", indexdef)

    def test_init_drops_the_constraint_of_an_older_version(self):
        """A table constraint on the same two columns, declared by no model any
        more: Odoo neither recreates nor removes it, so init has to."""
        self.env.cr.execute(
            "ALTER TABLE product_template ADD CONSTRAINT product_template_legacy_uniq"
            " UNIQUE (engineering_code, engineering_revision)"
        )
        self.env["product.template"].init()
        self.env.cr.execute(
            "SELECT count(*) FROM pg_constraint"
            " WHERE conrelid = 'product_template'::regclass AND contype = 'u'"
            "   AND conname = 'product_template_legacy_uniq'"
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)
        self.env.cr.execute(
            "SELECT count(*) FROM pg_indexes"
            " WHERE indexname = 'unique_index_product_template'"
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1)

    def test_the_index_stops_a_duplicate_past_the_checks(self):
        template = self._template("MC-P102")
        with mute_logger("odoo.sql_db"), self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.env.cr.execute(
                    "UPDATE product_template SET engineering_code = %s,"
                    " engineering_revision = 0 WHERE id = %s",
                    ("MC-P102", self._template("MC-P103").id),
                )
        self.assertTrue(template.exists())

    def test_init_with_duplicates_logs_and_goes_on(self):
        self.env.cr.execute("DROP INDEX unique_index_product_template")
        first = self._template("MC-P104")
        second = self._template("MC-P105")
        self.env.cr.execute(
            "UPDATE product_template SET engineering_code = 'MC-P104' WHERE id = %s",
            (second.id,),
        )
        with mute_logger("odoo.sql_db"), self.assertLogs(
            "odoo.addons.plm.models.plm_mixin", "ERROR"
        ) as logs:
            self.env["product.template"].init()
        self.assertIn("MC-P104 rev 0: 2 records", logs.output[0])
        self.assertTrue(first.exists())

    def test_placeholder_codes_are_no_code(self):
        for placeholder in ("", "-"):
            first = self._template(placeholder)
            second = self._template(placeholder)
            self.assertFalse(first.engineering_code)
            self.assertFalse(second.engineering_code)
        template = self._template("MC-P106")
        template.write({"engineering_code": "-"})
        self.assertFalse(template.engineering_code)

    def test_new_revision_number_counts_every_revision(self):
        template = self._template("MC-P107")
        template.engineering_state = "released"
        self._template("MC-P107", revision=4).engineering_state = "released"
        new_revision = template._new_version()
        self.assertEqual(new_revision.engineering_revision, 5)
