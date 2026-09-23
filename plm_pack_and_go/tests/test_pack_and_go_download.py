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
Created on 22 Sep 2026

@author: mboscolo
"""
import base64

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

#
#
# --test-tags=odoo_pack_and_go_download
#
#

# The smallest possible zip: an end of central directory record and nothing
# else. The wizard produces one just like it when no row is selected.
EMPTY_ZIP = b"PK\x05\x06" + b"\x00" * 18


#
@tagged(
    "-standard",
    "-at_install",
    "post_install",
    "odoo_pack_and_go",
    "odoo_pack_and_go_download",
)
class PackAndGoDownload(HttpCase):
    """The archive is downloaded from the controller, with a GET.

    The binary field widget used to download it with a POST, which carries a
    CSRF token: a page opened before the session was renewed answered
    "Session expired (invalid CSRF token)" instead of the archive.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = cls._user("pack_and_go_owner")
        cls.stranger = cls._user("pack_and_go_stranger")
        cls.component = cls.env["product.template"].create(
            {"name": "Pack and Go download", "engineering_code": "PACK_AND_GO_DOWNLOAD"}
        )
        cls.wizard = (
            cls.env["pack.and_go"]
            .with_user(cls.owner)
            .create(
                {
                    "component_id": cls.component.id,
                    "datas": base64.b64encode(EMPTY_ZIP),
                    "datas_fname": "pack_and_go.zip",
                }
            )
        )

    @classmethod
    def _user(cls, login):
        groups = cls.env.ref("base.group_user") | cls.env.ref(
            "plm.group_plm_integration_user"
        )
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "password": login,
                "group_ids": [Command.set(groups.ids)],
            }
        )

    def _download(self, wizard_id):
        return self.url_open("/plm_pack_and_go/download/%s" % wizard_id)

    def test_the_owner_downloads_the_archive(self):
        self.authenticate("pack_and_go_owner", "pack_and_go_owner")
        response = self._download(self.wizard.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, EMPTY_ZIP)
        self.assertIn(
            "pack_and_go.zip", response.headers.get("Content-Disposition", "")
        )
        self.assertIn(
            "attachment", response.headers.get("Content-Disposition", "")
        )

    def test_another_user_does_not_get_the_archive(self):
        self.authenticate("pack_and_go_stranger", "pack_and_go_stranger")
        self.assertEqual(self._download(self.wizard.id).status_code, 404)

    def test_an_unknown_wizard_is_not_found(self):
        self.authenticate("pack_and_go_owner", "pack_and_go_owner")
        last = self.env["pack.and_go"].search([], order="id desc", limit=1)
        self.assertEqual(self._download(last.id + 1000).status_code, 404)

    def test_the_export_returns_the_download_url(self):
        """The button hands the web client a url to GET, not a binary field."""
        wizard = (
            self.env["pack.and_go"]
            .with_user(self.owner)
            .create({"component_id": self.component.id})
        )
        action = wizard.action_export_zip()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "self")
        self.assertEqual(action["url"], "/plm_pack_and_go/download/%s" % wizard.id)
        self.assertTrue(wizard.datas, "the wizard holds the archive it built")

        self.authenticate("pack_and_go_owner", "pack_and_go_owner")
        response = self.url_open(action["url"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content[:2], b"PK", "a zip comes back")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
