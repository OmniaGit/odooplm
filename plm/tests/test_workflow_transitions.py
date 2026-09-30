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
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_workflow
#


@tagged("-standard", "odoo_plm_workflow")
class PlmWorkflowTransitions(TransactionCase, PlmEntityCreator):
    """move_to_state calls action_from_<from>_to_<to>: every move the
    obsolete and reactivate actions ask for has to exist (issue #110).

    An obsoleted record never goes back to draft: reactivating it releases it
    again, and only while no newer revision of its code is released.
    """

    def _released_document(self, name):
        document = self.create_document(name)
        document.is_plm = True
        document.action_confirm()
        document.action_release()
        self.assertEqual(document.engineering_state, "released")
        return document

    def test_document_obsolete_and_reactivate(self):
        document = self._released_document("wf_document")
        release_date = document.engineering_release_date
        document.action_obsolete()
        self.assertEqual(document.engineering_state, "obsoleted")
        document.action_reactivate()
        self.assertEqual(document.engineering_state, "released")
        self.assertEqual(document.engineering_release_date, release_date)

    def test_component_obsolete_and_reactivate(self):
        """A component and its document are obsoleted and reactivated
        together, keeping the date of their first release."""
        product = self.create_product_product("wf_component")
        document = self.create_document("wf_component_document")
        product.linkeddocuments = [(4, document.id)]
        product.action_confirm()
        product.action_release()
        self.assertEqual(product.engineering_state, "released")
        self.assertEqual(document.engineering_state, "released")
        release_date = product.engineering_release_date
        self.assertTrue(release_date)

        product.action_obsolete()
        self.assertEqual(product.engineering_state, "obsoleted")
        self.assertEqual(document.engineering_state, "obsoleted")

        product.action_reactivate()
        self.assertEqual(product.engineering_state, "released")
        self.assertEqual(document.engineering_state, "released")
        self.assertEqual(product.engineering_release_date, release_date)

    def _obsoleted_by_a_new_revision(self, name):
        """Revision 0 obsoleted because revision 1 was released."""
        rev_0 = self._released_document(name)
        rev_0.new_version()
        rev_1 = rev_0.get_next_version()
        rev_1.action_confirm()
        rev_1.action_release()
        self.assertEqual(rev_1.engineering_state, "released")
        self.assertEqual(rev_0.engineering_state, "obsoleted")
        return rev_0, rev_1

    def test_reactivate_refused_while_a_newer_revision_is_released(self):
        """One code never has two valid revisions."""
        rev_0, rev_1 = self._obsoleted_by_a_new_revision("wf_newer_released")
        with self.assertRaises(UserError) as refused:
            rev_0.action_reactivate()
        self.assertIn("newer revision", str(refused.exception))
        self.assertEqual(rev_0.engineering_state, "obsoleted")
        self.assertEqual(rev_1.engineering_state, "released")

    def test_reactivate_allowed_when_the_newer_revision_is_obsoleted(self):
        rev_0, rev_1 = self._obsoleted_by_a_new_revision("wf_newer_obsoleted")
        rev_1.action_obsolete()
        rev_0.action_reactivate()
        self.assertEqual(rev_0.engineering_state, "released")

    def test_reactivate_refused_unless_obsoleted(self):
        """On a confirmed record reactivate would release it skipping the
        release."""
        document = self.create_document("wf_confirmed")
        document.action_confirm()
        with self.assertRaises(UserError):
            document.action_reactivate()
        self.assertEqual(document.engineering_state, "confirmed")

    def test_under_modify_is_obsoleted(self):
        document = self._released_document("wf_under_modify")
        document.with_context(check=False).engineering_state = "undermodify"
        document.move_to_state("obsoleted")
        self.assertEqual(document.engineering_state, "obsoleted")
