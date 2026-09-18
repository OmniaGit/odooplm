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

    # the markup

    def _markup(self, login, res_model, res_id, **values):
        self.authenticate(login, login)
        payload = {
            "image": "data:image/jpeg;base64,%s" % CONTENT.decode(),
            "filename": "markup.jpg",
            "comment": "a note",
            "res_model": res_model,
            "res_id": res_id,
        }
        payload.update(values)
        response = self.url_open("/plm/save_markup", json={"params": payload})
        return json.loads(response.content)["result"]

    def test_a_markup_lands_on_the_document(self):
        answer = self._markup("web3d_insider", "ir.attachment", self.document.id)
        self.assertTrue(answer["success"])
        log = self.env["plm.markup.log"].sudo().browse(answer["markup_id"])
        self.assertEqual(log.create_uid, self.insider, "the author is the user")
        self.assertEqual(log.res_id, self.document.id)

    def test_no_markup_on_a_document_that_is_not_theirs(self):
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            answer = self._markup("web3d_outsider", "ir.attachment", self.document.id)
        self.assertEqual(answer, {"success": False})
        self.assertFalse(
            self.env["plm.markup.log"].sudo().search_count([("res_id", "=", self.document.id)])
        )

    def test_no_markup_on_a_model_the_viewer_does_not_work_on(self):
        """It took the model and the id from the caller and browsed them under
        sudo: any record of the database could be given a message."""
        partner = self.env["res.partner"].create({"name": "3d markup target"})
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            answer = self._markup("web3d_insider", "res.partner", partner.id)
        self.assertEqual(answer, {"success": False})
        self.assertFalse(partner.message_ids.filtered(lambda m: "a note" in (m.body or "")))

    def test_the_activity_goes_to_an_internal_user(self):
        portal = self.env["res.users"].create(
            {
                "name": "web3d_activity_portal",
                "login": "web3d_activity_portal",
                "group_ids": [Command.set(self.env.ref("base.group_portal").ids)],
            }
        )
        answer = self._markup(
            "web3d_insider",
            "ir.attachment",
            self.document.id,
            schedule_activity=True,
            activity_user_id=portal.id,
        )
        self.assertTrue(answer["success"])
        activity = self.env["mail.activity"].sudo().search(
            [("res_id", "=", self.document.id)], limit=1
        )
        self.assertTrue(activity)
        self.assertEqual(activity.user_id, self.insider, "not the portal user named")

    # the portal

    def _portal_customer(self, level, login="web3d_portal"):
        partner = self.env["res.partner"].create({"name": "3d portal customer"})
        partner.plm_portal_access = level
        user = self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "password": login,
                "partner_id": partner.id,
                "group_ids": [Command.set(self.env.ref("base.group_portal").ids)],
            }
        )
        self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [Command.create({"product_id": self.component.id})],
            }
        )
        return user

    def test_a_customer_opens_what_was_sold_to_them(self):
        """The viewer file of their own machine, and nothing else."""
        viewer_document = self.env["ir.attachment"].create(
            {
                "name": "WEB3D-1.3mf",
                "engineering_code": "WEB3D-1-3MF",
                "datas": CONTENT,
                "is_plm": True,
                "plm_access_id": self.node.id,
            }
        )
        viewer_document.linkedcomponents = self.component
        self._portal_customer("view")
        self.authenticate("web3d_portal", "web3d_portal")
        page = self.url_open(
            "/plm/show_treejs_model?document_id=%s&document_name=WEB3D-1.3mf"
            % viewer_document.id
        )
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("markup_button_perm", page.text, "view only: no markup")
        model = self.url_open(
            "/plm/download_treejs_model?document_id=%s" % viewer_document.id
        )
        self.assertEqual(model.status_code, 200)
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            native = self.url_open(
                "/plm/download_treejs_model?document_id=%s" % self.document.id
            )
        self.assertNotEqual(native.status_code, 200, "never the native CAD file")

    def test_a_customer_allowed_to_markup_gets_the_commands(self):
        viewer_document = self.env["ir.attachment"].create(
            {
                "name": "WEB3D-2.3mf",
                "engineering_code": "WEB3D-2-3MF",
                "datas": CONTENT,
                "is_plm": True,
                "plm_access_id": self.node.id,
            }
        )
        viewer_document.linkedcomponents = self.component
        self._portal_customer("markup", login="web3d_portal_markup")
        self.authenticate("web3d_portal_markup", "web3d_portal_markup")
        page = self.url_open(
            "/plm/show_treejs_model?document_id=%s&document_name=WEB3D-2.3mf"
            % viewer_document.id
        )
        self.assertIn("markup_button_perm", page.text)

    def test_a_customer_does_not_paint_the_model(self):
        """Saving the part colours writes on the document: the viewer of a
        customer looks, it does not change what the drawing office keeps."""
        self._portal_customer("markup", login="web3d_portal_colors")
        self.document.sudo().linkedcomponents = self.component
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            self.assertEqual(
                self._save_colors("web3d_portal_colors", {"part-1": "#123456"}),
                {"success": False},
            )

    def test_a_stranger_opens_nothing(self):
        stranger = self.env["res.users"].create(
            {
                "name": "web3d_stranger",
                "login": "web3d_stranger",
                "password": "web3d_stranger",
                "group_ids": [Command.set(self.env.ref("base.group_portal").ids)],
            }
        )
        self.assertTrue(stranger)
        self.authenticate("web3d_stranger", "web3d_stranger")
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            page = self.url_open(
                "/plm/show_treejs_model?document_id=%s&document_name=x"
                % self.document.id
            )
        self.assertEqual(page.status_code, 404)

    def test_product_info_hides_the_engineering_data(self):
        with mute_logger("odoo.addons.plm_web_3d.controllers.main"):
            answer = json.dumps(self._product_info("web3d_outsider"))
        self.assertNotIn("WEB3D-1", answer)
        self.assertNotIn("WEB3D-COMP", answer)
