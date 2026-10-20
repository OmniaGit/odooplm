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
from odoo import Command
from odoo.tests import HttpCase, tagged

#
# --test-tags=odoo_plm_extra_file
#

GLB = b"glTF\x02\x00\x00\x00 a .glb of the CAD client"


@tagged("-standard", "odoo_plm_extra_file", "post_install", "-at_install")
class PlmExtraFileUpload(HttpCase):
    """/plm_document_upload/extra_file: the files the CAD client writes beside
    a document at its check-in, a .glb among them (OmniaGLTFConverter)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = cls.env.ref("base.group_user") | cls.env.ref("plm.group_plm_integration_user")
        cls.env["res.users"].create(
            {
                "name": "plm_extra_file",
                "login": "plm_extra_file",
                "password": "plm_extra_file",
                "group_ids": [Command.set(groups.ids)],
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "EXTRA-PART", "engineering_code": "EXTRA-PART"}
        )
        cls.native = cls.env["ir.attachment"].create(
            {
                "name": "extra_part.sldprt",
                "engineering_code": "EXTRA-PART",
                "engineering_revision": 2,
                "raw": b"native",
                "is_plm": True,
            }
        )
        cls.env["plm.component.document.rel"].createFromIds(cls.product, cls.native)

    def _upload(self, content=GLB, filename="EXTRA-PART_2_Default.glb", **params):
        self.authenticate("plm_extra_file", "plm_extra_file")
        data = {"doc_name": filename.rsplit(".", 1)[0], "doc_rev": "2", "filename": filename}
        data.update(params)
        return self.url_open(
            "/plm_document_upload/extra_file",
            data=data,
            files={"file_stream": (filename, content)},
        )

    def _uploaded(self, code="EXTRA-PART_2_Default", revision=2):
        return self.env["ir.attachment"].search(
            [("engineering_code", "=", code), ("engineering_revision", "=", revision)]
        )

    def _relations(self, child, kind=None):
        domain = [("child_id", "=", child.id)]
        if kind:
            domain.append(("link_kind", "=", kind))
        return self.env["ir.attachment.relation"].search(domain)

    def test_the_file_is_stored_as_it_was_sent(self):
        response = self._upload(related_attachment_id=str(self.native.id))
        self.assertEqual(response.status_code, 200)
        uploaded = self._uploaded()
        self.assertEqual(bytes(uploaded.raw), GLB)
        self.assertEqual(self._relations(uploaded).mapped("link_kind"), ["ExtraTree"])

    def test_a_glb_hangs_on_its_document_as_its_3d_file(self):
        response = self._upload(related_attachment_id=str(self.native.id), link_kind="Web3DTree")
        self.assertEqual(response.status_code, 200)
        uploaded = self._uploaded()
        self.assertEqual(uploaded.name, "EXTRA-PART_2_Default.glb")
        relation = self._relations(uploaded)
        self.assertEqual(relation.mapped("link_kind"), ["Web3DTree"])
        self.assertEqual(relation.parent_id, self.native)
        self.assertIn(self.product, uploaded.linkedcomponents)
        if "has_web3d" in self.native._fields:
            self.native.invalidate_recordset(["has_web3d"])
            self.assertTrue(self.native.has_web3d)

    def test_the_document_by_its_code_and_revision(self):
        """An assembly's check-in writes the files of its parts: the client
        names their documents by code and revision, not by id."""
        response = self._upload(
            filename="EXTRA-PART_2_Long.glb",
            doc_name="EXTRA-PART_2_Long",
            related_engineering_code="EXTRA-PART",
            related_engineering_revision="2",
            link_kind="Web3DTree",
        )
        self.assertEqual(response.status_code, 200)
        uploaded = self._uploaded("EXTRA-PART_2_Long")
        self.assertEqual(self._relations(uploaded, "Web3DTree").parent_id, self.native)
        self.assertIn(self.product, uploaded.linkedcomponents)

    def test_an_unknown_document_is_refused(self):
        response = self._upload(
            related_engineering_code="NO-SUCH-CODE",
            related_engineering_revision="0",
            link_kind="Web3DTree",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self._uploaded())

    def test_only_the_relations_of_the_files_beside_a_document(self):
        """HiTree and the others drive the check-out and the download: not this route's"""
        response = self._upload(related_attachment_id=str(self.native.id), link_kind="HiTree")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self._uploaded())

    def test_no_document_no_relation(self):
        response = self._upload(product_id=str(self.product.id))
        self.assertEqual(response.status_code, 200)
        uploaded = self._uploaded()
        self.assertTrue(uploaded)
        self.assertFalse(self._relations(uploaded))
        self.assertIn(self.product, uploaded.linkedcomponents)

    def test_a_new_check_in_refreshes_the_file(self):
        self._upload(related_attachment_id=str(self.native.id), link_kind="Web3DTree")
        self._upload(content=GLB + b" again", related_attachment_id=str(self.native.id), link_kind="Web3DTree")
        uploaded = self._uploaded()
        self.assertEqual(len(uploaded), 1)
        self.assertEqual(bytes(uploaded.raw), GLB + b" again")
        self.assertEqual(len(self._relations(uploaded, "Web3DTree")), 1)
