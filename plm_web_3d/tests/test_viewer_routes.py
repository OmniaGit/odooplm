# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
import json

from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

#
# --test-tags=odoo_plm_web_3d_routes
#

CONTENT = base64.b64encode(b"solid")


@tagged("-standard", "odoo_plm_web_3d_routes", "post_install", "-at_install")
class PlmWeb3dRoutes(HttpCase):
    """The viewer routes answer what the user may read: they used to read every
    document by its id, under sudo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_rd = cls.env["res.groups"].create({"name": "PLM 3d R&D"})
        cls.node = cls.env["plm.access"].create(
            {
                "name": "3d R&D",
                "parent_id": cls.env.company.plm_access_id.id,
                "read_group_ids": [Command.set(cls.group_rd.ids)],
            }
        )
        cls.document = cls.env["ir.attachment"].create(
            {
                "name": "WEB3D-1.stl",
                "engineering_code": "WEB3D-1",
                "datas": CONTENT,
                "is_plm": True,
                "document_type": "3d",
                "plm_access_id": cls.node.id,
            }
        )
        cls.component = cls.env["product.product"].create({"name": "WEB3D-COMP"})
        cls.document.linkedcomponents = cls.component
        cls.outsider = cls._user("web3d_outsider")
        cls.insider = cls._user("web3d_insider", cls.group_rd)

    @classmethod
    def _user(cls, login, extra_group=None):
        groups = cls.env.ref("base.group_user") | cls.env.ref(
            "plm.group_plm_integration_user"
        )
        if extra_group:
            groups |= extra_group
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "password": login,
                "group_ids": [Command.set(groups.ids)],
            }
        )

    def _product_info(self, login):
        self.authenticate(login, login)
        response = self.url_open(
            "/plm/get_product_info?document_id=%s" % self.document.id
        )
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)

    def test_product_info_follows_the_node(self):
        self.assertIn("document", self._product_info("web3d_insider"))
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            self.assertEqual(self._product_info("web3d_outsider"), {})

    def test_product_info_hides_the_engineering_data(self):
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            answer = json.dumps(self._product_info("web3d_outsider"))
        self.assertNotIn("WEB3D-1", answer)
        self.assertNotIn("WEB3D-COMP", answer)
