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
Created on 17 Oct 2026

@author: mboscolo
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

#
# --test-tags=odoo_plm_recent_documents
#


@tagged("-standard", "odoo_plm_recent_documents")
class PlmClientRecentDocuments(TransactionCase):
    """plm.client.get_recent_documents: the CAD client's Recent files."""

    def setUp(self):
        super().setUp()
        self.documents = self.env["ir.attachment"].create(
            [{"name": "recent_%d.sldprt" % i, "engineering_code": "RECENT-%d" % i}
             for i in range(4)])
        self.other_user = self.env["res.users"].create(
            {"name": "Other designer", "login": "other_recent_designer"})

    def use(self, document, operation, user=None):
        return self.env["plm.cad.open"].sudo().create({
            "userid": (user or self.env.user).id, "document_id": document.id,
            "hostname": "host", "pws_path": "c:/pws", "operation_type": operation})

    def test_the_last_used_first_once_each(self):
        d0, d1, d2, _d3 = self.documents
        self.use(d0, "open")
        self.use(d1, "save")
        self.use(d0, "save")        # d0 used again: it comes first, once
        self.use(d2, "check-out")
        recent = self.env["plm.client"].get_recent_documents()
        self.assertEqual([d2.id, d0.id, d1.id], [r["document_id"] for r in recent])
        self.assertEqual(["check-out", "save", "save"], [r["operation_type"] for r in recent])

    def test_the_limit_is_the_querys(self):
        for document in self.documents:
            self.use(document, "open")
        recent = self.env["plm.client"].get_recent_documents(2)
        self.assertEqual([self.documents[3].id, self.documents[2].id],
                         [r["document_id"] for r in recent])

    def test_only_the_users_own(self):
        self.use(self.documents[0], "open", user=self.other_user)
        self.use(self.documents[1], "open")
        recent = self.env["plm.client"].get_recent_documents()
        self.assertEqual([self.documents[1].id], [r["document_id"] for r in recent])
