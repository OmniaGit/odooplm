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
Created on 9 Set 2023

@author: mboscolo
"""
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
#
# --test-tags=odoo_plm
#
#


#
@tagged("-standard", "odoo_plm_check_in")
class PlmDateBom(TransactionCase, PlmEntityCreator):

    def test_workflow_refuses_a_document_that_is_checked_out(self):
        """A state is a statement about the whole of a component.

        A document somebody still has out is a file nobody else has seen, so
        the move is refused and the message says which document it is and who
        has it.

        It went the other way until 2026-09-14: the error was appended in a
        branch that could not be reached -- the outer condition already
        required check_in_check -- so every move jumped the checked out
        document in silence and left the component ahead of its own drawing.

        The document is taken out while it is still draft, which is the only
        state a check-out is allowed from, and it is the first move of the
        component that has to refuse.
        """
        product, document = self.create_product_document("workflow_check_in")
        document.checkout("web", "-", True)
        with self.assertRaises(UserError) as refused:
            product.action_confirm()
        self.assertIn(document.name, str(refused.exception))
        self.assertIn("Check-In All the document", str(refused.exception))
        self.assertEqual(document.engineering_state, "draft")

    def test_workflow_moves_when_every_document_is_in(self):
        """And the same move goes through once the document is back."""
        product, document = self.create_product_document("workflow_check_in_ok")
        document.checkout("web", "-", True)
        document._check_in()
        product.action_confirm()
        self.assertEqual(product.engineering_state, "confirmed")
        self.assertEqual(document.engineering_state, "confirmed")

    def test_a_document_alone_is_refused_too(self):
        """The rule is about every workflow move, not about the ones a
        component drives: a document moved from its own statusbar is refused
        the same way, and by the same door.

        Until 2026-09-14 release skipped it in silence and the other actions
        did not look at all.
        """
        document = self.create_document("workflow_alone", doc_type="2d")
        document.checkout("web", "-", True)
        for action in ("action_confirm", "action_release", "action_obsolete"):
            with self.assertRaises(UserError) as refused:
                getattr(document, action)()
            self.assertIn(document.name, str(refused.exception))
        self.assertEqual(document.engineering_state, "draft")
        document._check_in()
        document.action_confirm()
        self.assertEqual(document.engineering_state, "confirmed")

    def test_a_document_without_a_code_is_not_another_one(self):
        """A drawing with no code asks the client door about nothing.

        Searching with an empty code matched every attachment without one, web
        assets included, and the save was refused as "in check-in" on behalf of
        the first of them (2026-09-14). For the CAD client only.
        """
        client = self.env["plm.client"].with_context(odooPLM=True)
        props = {"engineering_code": "", "engineering_revision": ""}
        self.assertFalse(client.getAttachmentFromProp(props))
        self.assertEqual(client.attachmentCanBeSaved(props), (True, ""))

    def test_check_in(self):
        level_0_3d = self.create_document("document_level_0_3d", doc_type="3d")
        level_0_3d.checkout("web", "-", True)
        level_0_2d = self.create_document("document_level_0_2d", doc_type="2d")
        level_0_2d.checkout("web", "-", True)
        level_0_2d_1 = self.create_document("document_level_0_2d_1", doc_type="2d")
        level_0_2d_1.checkout("web", "-", True)
        #
        self.create_link_document(level_0_3d, level_0_2d, "LyTree")
        self.create_link_document(level_0_3d, level_0_2d_1, "LyTree")

        level_1_3d = self.create_document("document_level_1_3d", doc_type="3d")
        level_1_3d.checkout("web", "-", True)
        level_1_3d_1 = self.create_document("document_level_1_3d_1", doc_type="3d")
        level_1_3d_1.checkout("web", "-", True)
        level_1_2d = self.create_document("document_level_1_2d", doc_type="2d")
        level_1_2d.checkout("web", "-", True)

        self.create_link_document(level_1_3d, level_1_2d, "LyTree")
        self.create_link_document(level_0_3d, level_1_3d, "HiTree")
        self.create_link_document(level_0_3d, level_1_3d_1, "HiTree")

        level_2_3d = self.create_document("document_level_2_3d", doc_type="3d")
        level_2_3d.checkout("web", "-", True)
        level_2_2d = self.create_document("document_level_2_2d", doc_type="2d")
        level_2_2d.checkout("web", "-", True)

        self.create_link_document(level_2_3d, level_2_2d, "LyTree")
        self.create_link_document(level_1_3d, level_2_3d, "HiTree")

        level_3_3d = self.create_document("document_level_3_3d", doc_type="3d")
        level_3_3d.checkout("web", "-", True)
        level_3_2d = self.create_document("document_level_3_2d", doc_type="2d")
        level_3_2d.checkout("web", "-", True)

        self.create_link_document(level_3_3d, level_3_2d, "LyTree")
        self.create_link_document(level_2_3d, level_3_3d, "HiTree")

        res = level_0_3d._preCheckInRecursive_all(level_0_3d)
        assert len(res["to_check_2d"]) == 5
        assert len(res["to_check_3d"]) == 5
        assert len(res["info"]) == 0

        level_3_2d._check_in()
        res = level_0_3d._preCheckInRecursive_all(level_0_3d)
        assert len(res["to_check_2d"]) == 4
        assert len(res["to_check_3d"]) == 5
        assert len(res["info"]) == 1

        level_3_2d.checkout(
            "web", "-", True, user_id=self.env.ref("base.default_user").id
        )
        res = level_0_3d._preCheckInRecursive_all(level_0_3d)
        assert len(res["to_check_2d"]) == 4
        assert len(res["to_check_3d"]) == 5
        assert len(res["info"]) == 1
