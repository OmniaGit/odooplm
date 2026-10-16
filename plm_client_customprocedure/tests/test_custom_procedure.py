# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from odoo.tests import HttpCase, tagged

#
# --test-tags=odoo_plm_customprocedure
#


def _b64(text):
    return base64.b64encode(text.encode()).decode()


@tagged("-standard", "odoo_plm_customprocedure", "post_install", "-at_install")
class TestCustomProcedure(HttpCase):
    """The CAD client gets its CustomProcedure over XML-RPC: the user's,
    else the one of the first of their groups that has one."""

    def setUp(self):
        super().setUp()
        self.admin = self.env.ref("base.user_admin")
        self.admin.custom_procedure = False
        self.admin.custom_multicad = False
        for group in self.admin.group_ids:
            group.custom_procedure = False
            group.custom_multicad = False

    def _client_call(self):
        """The call the CAD client makes, decoded as it decodes it."""
        value, name = self.xmlrpc_object.execute_kw(
            self.env.cr.dbname, self.admin.id, "admin",
            "res.users", "getCustomProcedure", [[]])
        return (base64.b64decode(value) if value else b""), name

    def test_none(self):
        self.assertEqual(self._client_call(), (b"", ""))

    def test_group_then_user(self):
        group = self.env["res.groups"].create({"name": "CP group", "custom_procedure": _b64("group = 1\n")})
        self.admin.group_ids = [(4, group.id)]
        # groups without a procedure come first and are skipped
        self.assertEqual(self._client_call(), (b"group = 1\n", "CustomProcedure.py"))
        self.admin.custom_procedure = _b64("user = 1\n")
        self.assertEqual(self._client_call(), (b"user = 1\n", "CustomProcedure.py"))

    def test_editor(self):
        group = self.env["res.groups"].create({"name": "CP editor"})
        group.write({"custom_read_content": "edited = 1\n"})
        self.assertEqual(group.custom_procedure.content, b"edited = 1\n")
        group.open_custommodule_edit()
        self.assertEqual(group.custom_read_content, "edited = 1\n")
        self.admin.write({"custom_read_content": "user_edited = 1\n"})
        self.assertEqual(self.admin.custom_procedure.content, b"user_edited = 1\n")

    def _rpc(self, model, method, ids):
        return self.xmlrpc_object.execute_kw(self.env.cr.dbname, self.admin.id, "admin", model, method, [ids])

    def test_multicad_group_then_user(self):
        self.assertEqual(self._rpc("res.users", "getCustomMulticad", []), ["", ""])
        group = self.env["res.groups"].create({"name": "MC group", "custom_multicad": _b64("group mc"),
                                               "custom_multicad_fname": "group.zip"})
        self.admin.group_ids = [(4, group.id)]
        value, name = self._rpc("res.users", "getCustomMulticad", [])
        self.assertEqual((base64.b64decode(value), name), (b"group mc", "group.zip"))
        self.admin.write({"custom_multicad": _b64("user mc"), "custom_multicad_fname": "user.zip"})
        value, name = self._rpc("res.users", "getCustomMulticad", [])
        self.assertEqual((base64.b64decode(value), name), (b"user mc", "user.zip"))

    def test_group_methods_over_rpc(self):
        group = self.env["res.groups"].create({"name": "RPC group", "custom_procedure": _b64("p = 1\n"),
                                               "custom_procedure_fname": "CustomProcedure.py",
                                               "custom_multicad": _b64("mc"), "custom_multicad_fname": "mc.zip"})
        found, value, name = self._rpc("res.groups", "getCustomProcedure", [group.id])
        self.assertEqual((found, base64.b64decode(value), name), (True, b"p = 1\n", "CustomProcedure.py"))
        found, value, name = self._rpc("res.groups", "getCustomMulticad", [group.id])
        self.assertEqual((found, base64.b64decode(value), name), (True, b"mc", "mc.zip"))
        self.assertEqual(self._rpc("res.groups", "getCustomMulticad", []), [False, "", ""])
