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
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_revision_chain
#


@tagged("-standard", "odoo_plm_revision_chain")
class PlmRevisionChain(TransactionCase, PlmEntityCreator):
    """A revision can be created by anyone -- new_version, the CAD client that
    computes its own revision, a historical import -- and with gaps: 3 in the
    db, 5 saved from the CAD. Whoever creates it, the chain of the code stays
    consistent.
    """

    CODE = "revision_chain_code"

    def _revision(self, revision, state):
        document = self.env["ir.attachment"].create(
            {
                "datas": "",
                "name": "%s_%s" % (self.CODE, revision),
                "engineering_code": self.CODE,
                "engineering_revision": revision,
                "res_model": "ir.attachment",
                "res_id": 0,
                "document_type": "2d",
            }
        )
        document.with_context(check=False).engineering_state = state
        return document

    def test_gap_marks_nearest_under_modify_and_obsoletes_the_rest(self):
        """The confirmed revision 3 is released ex officio and goes under
        modification; revision 1 has been in use and is obsoleted."""
        rev_1 = self._revision(1, "released")
        rev_3 = self._revision(3, "confirmed")
        self._revision(5, "draft")
        self.assertEqual(rev_3.engineering_state, "undermodify")
        self.assertEqual(rev_1.engineering_state, "obsoleted")

    def test_draft_below_refuses_the_creation(self):
        """A draft below means the code was never settled."""
        self._revision(3, "draft")
        with self.assertRaises(UserError) as refused:
            self._revision(5, "draft")
        self.assertIn("still in draft", str(refused.exception))
        self.assertFalse(
            self.env["ir.attachment"].search(
                [("engineering_code", "=", self.CODE), ("engineering_revision", "=", 5)]
            )
        )

    def test_checked_out_below_refuses_the_creation(self):
        """Moving its state is a workflow move, so it wants it checked in.

        A check-out is only allowed in draft, and a draft below is refused
        already: this is the inconsistent data the workflow let through until
        2026-09-14, a document confirmed while somebody still had it out.
        """
        rev_3 = self._revision(3, "draft")
        rev_3.checkout("web", "-", True)
        rev_3.with_context(check=False).engineering_state = "confirmed"
        with self.assertRaises(UserError) as refused:
            self._revision(5, "draft")
        self.assertIn(rev_3.name, str(refused.exception))

    def test_release_across_the_gap_obsoletes_the_previous(self):
        """Releasing 5 finds 3 even though 4 does not exist."""
        rev_3 = self._revision(3, "released")
        rev_5 = self._revision(5, "draft")
        self.assertEqual(rev_3.engineering_state, "undermodify")
        rev_5.action_from_confirmed_to_released()
        self.assertEqual(rev_3.engineering_state, "obsoleted")
