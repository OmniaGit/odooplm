# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2026 OmniaSolutions (<http://www.omniasolutions.eu>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
"""What the demo is supposed to look like once the module is installed.

These tests read the database the post_init_hook built; they create nothing. A
failure means the demo an evaluator sees is not the demo the module claims to
install — which is the only thing that makes this dataset worth shipping.

    odoo --test-tags=odoo_plm_demo -i plm_demo -d <database>
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-standard", "odoo_plm_demo")
class TestDemoLifecycle(TransactionCase):
    def part(self, xml_id):
        """The variant behind a demo part: the dataset registers templates."""
        return self.env.ref("plm_demo.%s" % xml_id).product_variant_id

    def document(self, xml_id):
        return self.env.ref("plm_demo.%s" % xml_id)

    def test_top_assembly_is_released(self):
        """The product as manufactured today: revision 0, released."""
        assembly = self.part("part_lsu_100")
        self.assertEqual(assembly.engineering_revision, 0)
        self.assertEqual(assembly.engineering_state, "released")

    def test_release_of_a_new_revision_obsoletes_the_previous_one(self):
        """Nothing writes 'obsoleted': releasing revision 1 does it."""
        old = self.part("part_scr_m6_020")
        new = self.part("part_scr_m6_020_rev1")
        self.assertEqual(new.engineering_revision, 1)
        self.assertEqual(new.engineering_code, old.engineering_code)
        self.assertEqual(new.engineering_state, "released")
        self.assertEqual(old.engineering_state, "obsoleted")

    def test_a_part_under_modification_keeps_its_revision_in_draft(self):
        old = self.part("part_brg_hsg_001")
        new = self.part("part_brg_hsg_001_rev1")
        self.assertEqual(old.engineering_state, "undermodify")
        self.assertEqual(new.engineering_revision, 1)
        self.assertEqual(new.engineering_state, "draft")
        self.assertTrue(new.desc_modify, "the reason for the revision is missing")

    def test_the_new_revision_carries_its_own_documents(self):
        """NewRevision clears the linked documents; the loader links them back."""
        new = self.part("part_brg_hsg_001_rev1")
        documents = self.env["ir.attachment"].search(
            [("linkedcomponents", "in", new.id)]
        )
        self.assertEqual(len(documents), 3, "expected the 3MF, the STEP and the sheet")
        for document in documents:
            self.assertEqual(document.engineering_revision, 1)

    def test_a_document_is_checked_out(self):
        document = self.document("doc_brg_hsg_001_drawing_dxf_rev1")
        checkout = self.env["plm.checkout"].search(
            [("documentid", "=", document.id)], limit=1
        )
        self.assertTrue(checkout, "the 2D sheet of the revision is not checked out")
        self.assertTrue(checkout.hostname)

    def test_an_open_change_order_sits_on_the_part(self):
        eco = self.env.ref("plm_demo.eco_brg_hsg_001")
        self.assertTrue(eco.is_eco)
        self.assertEqual(eco.plm_state, "eco")
        self.assertEqual(eco.res_id, self.part("part_brg_hsg_001").id)

    def test_the_change_request_is_closed_and_kept(self):
        """A closed request is archived, not deleted: _action_done archives.

        The history of why a part changed is the point of an ECR, so what is
        asserted is that it survives closing.
        """
        ecr = self.env.ref("plm_demo.ecr_brg_hsg_001")
        self.assertEqual(ecr.plm_state, "done")
        self.assertFalse(ecr.active, "a closed request should be archived")
        self.assertFalse(ecr.is_eco)

    def test_only_the_change_order_is_still_open(self):
        """The default search skips archived records: one open activity left."""
        part = self.part("part_brg_hsg_001")
        activities = self.env["mail.activity"].search(
            [("res_model", "=", "product.product"), ("res_id", "=", part.id)]
        )
        self.assertEqual(len(activities), 1)
        self.assertTrue(activities.is_eco)
