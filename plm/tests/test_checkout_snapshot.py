# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
"""
Created on 19 Sep 2026

@author: mboscolo
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_checkout_snapshot
#


@tagged("-standard", "odoo_plm_checkout_snapshot")
class PlmCheckoutSnapshot(TransactionCase, PlmEntityCreator):
    def _rows_by_file(self, answer):
        return {row["file_name"]: row for row in answer["rows"]}

    def test_rows_stamp_and_check_in(self):
        mine = self.create_document("snapshot_mine.SLDPRT", doc_type="3d")
        mine.checkout("PC-MINE", "C:/pws", True)
        # An existing user: creating one depends on every installed module
        # accepting the new partner, which not every test database does.
        other_user = self.env.ref("base.user_root")
        theirs = self.create_document("snapshot_theirs.SLDPRT", doc_type="3d")
        theirs.checkout("PC-OTHER", "D:/pws", True, user_id=other_user.id)
        client = self.env["plm.client"]

        first = client.get_checkout_snapshot()
        self.assertTrue(first["changed"])
        self.assertTrue(first["stamp"])
        rows = self._rows_by_file(first)
        self.assertEqual(rows["snapshot_mine.SLDPRT"]["user_id"], self.env.uid)
        self.assertEqual(rows["snapshot_mine.SLDPRT"]["hostname"], "PC-MINE")
        self.assertEqual(rows["snapshot_theirs.SLDPRT"]["user"], other_user.name)
        self.assertEqual(rows["snapshot_theirs.SLDPRT"]["user_id"], other_user.id)
        self.assertEqual(rows["snapshot_theirs.SLDPRT"]["document_id"], theirs.id)
        self.assertTrue(rows["snapshot_theirs.SLDPRT"]["checkout_date"])

        unchanged = client.get_checkout_snapshot(first["stamp"])
        self.assertFalse(unchanged["changed"])
        self.assertEqual(unchanged["stamp"], first["stamp"])
        self.assertEqual(unchanged["rows"], [])

        mine._check_in()
        after_check_in = client.get_checkout_snapshot(first["stamp"])
        self.assertTrue(after_check_in["changed"])
        self.assertNotEqual(after_check_in["stamp"], first["stamp"])
        rows = self._rows_by_file(after_check_in)
        self.assertNotIn("snapshot_mine.SLDPRT", rows)
        self.assertIn("snapshot_theirs.SLDPRT", rows)

    def test_states_of_the_files_asked_for(self):
        draft = self.create_document("snapshot_draft.SLDPRT", doc_type="3d")
        released = self.create_document("snapshot_released.SLDPRT", doc_type="3d")
        released.engineering_state = "released"
        client = self.env["plm.client"]
        asked = [draft.name, released.name, "snapshot_unknown.SLDPRT"]

        answer = client.get_checkout_snapshot(file_names=asked)
        states = {state["file_name"]: state["state"] for state in answer["states"]}
        # A draft document can be checked out, so it says nothing; neither does a
        # file no document carries.
        self.assertEqual(states, {"snapshot_released.SLDPRT": "released"})

        unchanged = client.get_checkout_snapshot(answer["stamp"], file_names=asked)
        self.assertFalse(unchanged["changed"])
        self.assertEqual(unchanged["states"], [])

        released.engineering_state = "obsoleted"
        after = client.get_checkout_snapshot(answer["stamp"], file_names=asked)
        self.assertTrue(after["changed"])
        states = {state["file_name"]: state["state"] for state in after["states"]}
        self.assertEqual(states, {"snapshot_released.SLDPRT": "obsoleted"})

        # The files the helper does not ask about are not answered for.
        without = client.get_checkout_snapshot()
        self.assertEqual(without["states"], [])

    def test_the_last_revision_answers_for_the_file(self):
        released = self.create_document("snapshot_revised.SLDPRT", doc_type="3d")
        released.engineering_state = "released"
        client = self.env["plm.client"]
        asked = [released.name]

        states = {
            state["file_name"]: state["state"]
            for state in client.get_checkout_snapshot(file_names=asked)["states"]
        }
        self.assertEqual(states, {"snapshot_revised.SLDPRT": "released"})

        # A new revision of the same file: it is in draft and can be checked out,
        # so the released revision behind it must say nothing.
        draft = released.copy(
            {
                "engineering_revision": released.engineering_revision + 1,
                "engineering_state": "draft",
            }
        )
        self.assertEqual(draft.name, released.name)
        answer = client.get_checkout_snapshot(file_names=asked)
        self.assertEqual(answer["states"], [])
