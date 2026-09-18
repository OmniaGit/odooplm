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

    def test_part_colors_load_follows_the_node(self):
        self.document.sudo().web3d_part_colors = '{"part-1": "#ff0000"}'
        self.authenticate("web3d_insider", "web3d_insider")
        mine = self.url_open(
            "/plm/part_colors/load?document_id=%s" % self.document.id
        )
        self.assertIn("part-1", mine.text)
        self.authenticate("web3d_outsider", "web3d_outsider")
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            theirs = self.url_open(
                "/plm/part_colors/load?document_id=%s" % self.document.id
            )
        self.assertEqual(json.loads(theirs.text), {})

    def _save_colors(self, login, colors):
        self.authenticate(login, login)
        response = self.url_open(
            "/plm/part_colors/save",
            json={
                "params": {
                    "document_id": self.document.id,
                    "colors": colors,
                }
            },
        )
        return json.loads(response.content)["result"]

    def test_part_colors_save_follows_the_node(self):
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            self.assertEqual(
                self._save_colors("web3d_outsider", {"part-1": "#00ff00"}),
                {"success": False},
            )
        self.assertFalse(self.document.web3d_part_colors)
        self.assertEqual(
            self._save_colors("web3d_insider", {"part-1": "#00ff00"}),
            {"success": True},
        )
        self.assertIn("#00ff00", self.document.web3d_part_colors)

    def test_part_colors_save_needs_the_write_right(self):
        """Reading the document is not writing it: a readonly level may not."""
        reader = self.env["res.users"].create(
            {
                "name": "web3d_reader",
                "login": "web3d_reader",
                "password": "web3d_reader",
                "group_ids": [
                    Command.set(
                        (
                            self.env.ref("base.group_user")
                            | self.env.ref("plm.group_plm_view_user")
                            | self.group_rd
                        ).ids
                    )
                ],
            }
        )
        self.assertTrue(reader)
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            self.assertEqual(
                self._save_colors("web3d_reader", {"part-1": "#0000ff"}),
                {"success": False},
            )

    def test_product_info_hides_the_engineering_data(self):
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            answer = json.dumps(self._product_info("web3d_outsider"))
        self.assertNotIn("WEB3D-1", answer)
        self.assertNotIn("WEB3D-COMP", answer)
