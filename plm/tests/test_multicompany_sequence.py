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
import importlib.util

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path

#
# --test-tags=odoo_plm_multicompany
#

PLM_SEQUENCES = (
    "plm.seq_plm_finishing",
    "plm.seq_plm_description",
    "plm.seq_plm_treatment",
    "plm.seq_plm_material",
    "plm.sequence_document",
    "plm.sequence_plm_dbthread",
)


@tagged("-standard", "odoo_plm_multicompany")
class PlmMultiCompanySequence(TransactionCase):
    """The PLM sequences are global: every company draws from the same counter,
    unless an administrator gives a company its own copy."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env["res.company"].create({"name": "PLM company B"})

    def test_sequences_are_global(self):
        for xmlid in PLM_SEQUENCES:
            self.assertFalse(self.env.ref(xmlid).company_id, xmlid)

    def test_document_name_in_another_company(self):
        """GetNextDocumentName concatenated False and raised TypeError."""
        attachment = self.env["ir.attachment"].with_company(self.company_b)
        name = attachment.GetNextDocumentName("DOC")
        self.assertTrue(name.startswith("DOC-"))
        self.assertNotIn("False", name)

    def test_companies_share_the_counter(self):
        sequence = self.env["ir.sequence"]
        first = sequence.next_by_code("plm.dbthread.progress")
        second = sequence.with_company(self.company_b).next_by_code(
            "plm.dbthread.progress"
        )
        self.assertTrue(first and second)
        self.assertEqual(int(second), int(first) + 1)

    def test_own_copy_wins_over_the_global_sequence(self):
        """The documented way to give a company its own numbering."""
        self.env.ref("plm.sequence_plm_dbthread").copy(
            {"company_id": self.company_b.id, "prefix": "B-"}
        )
        sequence = self.env["ir.sequence"]
        self.assertTrue(
            sequence.with_company(self.company_b)
            .next_by_code("plm.dbthread.progress")
            .startswith("B-")
        )
        self.assertFalse(
            sequence.next_by_code("plm.dbthread.progress").startswith("B-")
        )

    def test_sequence_from_is_shared(self):
        template = self.env["product.template"]
        first = template.with_company(self.company_b).getSequenceFrom("MCT", 4)
        second = template.getSequenceFrom("MCT", 4)
        created = self.env["ir.sequence"].search([("code", "=", "PLM_SEQUENCE_MCT")])
        self.assertEqual(len(created), 1)
        self.assertFalse(created.company_id)
        self.assertNotEqual(first, second)

    def test_upgrade_makes_bound_sequences_global(self):
        bound = self.env.ref("plm.sequence_document")
        bound.company_id = self.env.company
        by_hand = self.env["ir.sequence"].create(
            {"name": "by hand", "code": "plm.test.by_hand", "company_id": self.env.company.id}
        )
        path = file_path("plm/upgrades/18.0.21.0.28/post-migrate.py")
        spec = importlib.util.spec_from_file_location("plm_post_migrate", path)
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        self.env.flush_all()
        script.migrate(self.env.cr, "18.0.21.0.27")
        self.env.invalidate_all()
        self.assertFalse(bound.company_id)
        self.assertEqual(by_hand.company_id, self.env.company)
