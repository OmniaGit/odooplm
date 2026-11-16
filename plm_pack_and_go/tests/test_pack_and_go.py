# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Created on 9 Set 2023

@author: mboscolo
"""
import json
import logging
import datetime
import zipfile
from io import BytesIO
from odoo import models, Command, fields, api, _
from odoo.tests import tagged
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests.common import TransactionCase
from odoo.addons.plm.models.plm_mixin import (
    RELEASED_STATUS,
    UNDER_MODIFY_STATUS,
    START_STATUS,
    CONFIRMED_STATUS,
    OBSOLATED_STATUS,
)
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
#
# --test-tags=odoo_pack_and_go
#
#

#
@tagged("-standard", "odoo_pack_and_go")
class PlmDateBom(TransactionCase, PlmEntityCreator):
    def test_pack_and_go(self):
        product, _bom = self.get_3_level_assembly("pack_and_go")
        other_attachment = self.create_document("parent_other_attachment")
        other_attachment.linkedcomponents = [(4, product.id)]
        pack_and_go_id = self.env["pack.and_go"].create(
            {"component_id": product.product_tmpl_id.id}
        )
        for export_type in ["2d", "3d", "pdf", "2dpdf", "3dpdf", "3d2d", "all"]:
            pack_and_go_id.export_type_id = self.env.ref(
                f"plm_pack_and_go.pack_go_export_type_{export_type}"
            )
            pack_and_go_id.bom_computation = "ONLY_PRODUCT"
            pack_and_go_id.action_compute_attachment_bom()
            if export_type == "2d":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "3d":
                assert (
                    len(pack_and_go_id.export_3d) == 10
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "pdf":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "2dpdf":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "3d2d":
                assert (
                    len(pack_and_go_id.export_3d) == 10
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "all":
                assert (
                    len(pack_and_go_id.export_3d) == 10
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            pack_and_go_id.bom_computation = "FIRST_LEVEL"
            pack_and_go_id.action_compute_attachment_bom()
            if export_type == "2d":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "3d":
                assert (
                    len(pack_and_go_id.export_3d) == 8
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "pdf":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "2dpdf":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "3d2d":
                assert (
                    len(pack_and_go_id.export_3d) == 8
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "all":
                assert (
                    len(pack_and_go_id.export_3d) == 8
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            pack_and_go_id.bom_computation = "ALL_LEVEL"
            pack_and_go_id.action_compute_attachment_bom()
            if export_type == "2d":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 5
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "3d":
                assert (
                    len(pack_and_go_id.export_3d) == 10
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "pdf":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 5
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "2dpdf":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 5
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 5
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "3d2d":
                assert (
                    len(pack_and_go_id.export_3d) == 10
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 5
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "all":
                assert (
                    len(pack_and_go_id.export_3d) == 10
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 5
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 5
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 1
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            pack_and_go_id.bom_computation = "LEAF"
            pack_and_go_id.action_compute_attachment_bom()
            if export_type == "2d":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "3d":
                assert (
                    len(pack_and_go_id.export_3d) == 4
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "pdf":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "2dpdf":
                assert (
                    len(pack_and_go_id.export_3d) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "3d2d":
                assert (
                    len(pack_and_go_id.export_3d) == 4
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"
            elif export_type == "all":
                assert (
                    len(pack_and_go_id.export_3d) == 4
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_3d}"
                assert (
                    len(pack_and_go_id.export_2d) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_2d}"
                assert (
                    len(pack_and_go_id.export_pdf) == 2
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_pdf}"
                assert (
                    len(pack_and_go_id.export_other) == 0
                ), f"{export_type} {pack_and_go_id.bom_computation} {pack_and_go_id.export_other}"

    def _get_export_document_ids(self, pack_and_go_id):
        rows = (
            pack_and_go_id.export_2d
            + pack_and_go_id.export_3d
            + pack_and_go_id.export_pdf
            + pack_and_go_id.export_other
        )
        return rows.document_id

    def _prepare_pack_and_go(self, name):
        product, _bom = self.get_3_level_assembly(name)
        pack_and_go_id = self.env["pack.and_go"].create(
            {"component_id": product.product_tmpl_id.id}
        )
        pack_and_go_id.export_type_id = self.env.ref(
            "plm_pack_and_go.pack_go_export_type_all"
        )
        pack_and_go_id.bom_computation = "ALL_LEVEL"
        pack_and_go_id.action_compute_attachment_bom()
        return pack_and_go_id, self._get_export_document_ids(pack_and_go_id)

    def test_pack_and_go_export_without_checkout(self):
        """"Download zip" (action_export_zip): today's behavior, unchanged,
        no document is checked out and no manifest is added."""
        pack_and_go_id, document_ids = self._prepare_pack_and_go(
            "pack_and_go_no_checkout"
        )
        pack_and_go_id.action_export_zip()
        self.assertFalse(
            self.env["plm.checkout"].search(
                [("documentid", "in", document_ids.ids)]
            ),
            "no document should be checked out by plain Download zip",
        )
        with zipfile.ZipFile(BytesIO(bytes(pack_and_go_id.datas))) as zip_file:
            self.assertNotIn("exported_data.json", zip_file.namelist())

    def test_pack_and_go_export_with_checkout(self):
        """"Create zip archive checkout" (action_create_zip_checkout): every
        exported document gets locked and a manifest listing them is added
        to the zip."""
        pack_and_go_id, document_ids = self._prepare_pack_and_go(
            "pack_and_go_checkout"
        )
        self.assertTrue(document_ids, "expected at least one document to export")
        pack_and_go_id.action_create_zip_checkout()
        checkouts = self.env["plm.checkout"].search(
            [("documentid", "in", document_ids.ids)]
        )
        self.assertEqual(
            len(checkouts),
            len(document_ids),
            "every exported document should be checked out",
        )
        with zipfile.ZipFile(BytesIO(bytes(pack_and_go_id.datas))) as zip_file:
            self.assertIn("exported_data.json", zip_file.namelist())
            manifest = json.loads(zip_file.read("exported_data.json"))
        self.assertEqual(
            {row["id"] for row in manifest["ir_attachment"]}, set(document_ids.ids)
        )

    def test_pack_and_go_checkout_blocked_by_other_user(self):
        """One document already checked out by someone else must abort the
        whole export: no document, including the others, ends up locked."""
        pack_and_go_id, document_ids = self._prepare_pack_and_go(
            "pack_and_go_checkout_blocked"
        )
        self.assertGreater(
            len(document_ids), 1, "need more than one document to prove the rollback"
        )
        other_user = self.env["res.users"].create(
            {
                "name": "Pack and Go other user",
                "login": "pack_and_go_other_user",
            }
        )
        blocked_document = document_ids[0]
        other_documents = document_ids[1:]
        self.env["plm.checkout"].create(
            {
                "documentid": blocked_document.id,
                "userid": other_user.id,
                "hostname": "test",
                "hostpws": "C:\\test",
            }
        )

        with self.assertRaises(UserError):
            pack_and_go_id.action_create_zip_checkout()

        self.assertFalse(
            self.env["plm.checkout"].search(
                [("documentid", "in", other_documents.ids)]
            ),
            "no other document should end up checked out: the export must be all or nothing",
        )
