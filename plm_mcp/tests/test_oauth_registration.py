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
"""How an application becomes known: by its metadata address, or by asking.

    odoo --test-tags=odoo_plm_mcp -u plm_mcp -d <database>

The network is never touched: the one method that fetches a metadata document
is replaced, and the lower-level pieces (DNS, the HTTP call) are replaced where
they are tested on their own. A test that reached claude.ai would pass or fail
on the day's weather.
"""
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm_mcp.models import plm_mcp_oauth_client as client_module
from odoo.addons.plm_mcp.models.plm_mcp_oauth_client import (
    NAME_MAX,
    PARAM_CIMD,
    PARAM_DCR,
    assert_public_host,
    clean_name,
)

from .test_oauth import REDIRECT, OauthHttpCase

REGISTER = "/plm/oauth/register"
URL = "https://assistant.example/oauth/client.json"


@tagged("-standard", "odoo_plm_mcp")
class TestNetworkSafety(TransactionCase):
    """The pieces that stand between the server and the address it is given."""

    def resolves_to(self, *addresses):
        infos = [(2, 1, 6, "", (address, 443)) for address in addresses]
        return patch.object(client_module.socket, "getaddrinfo", return_value=infos)

    def test_a_public_address_is_accepted(self):
        with self.resolves_to("93.184.216.34"):
            assert_public_host("assistant.example")

    def test_a_private_address_is_refused(self):
        for address in ("127.0.0.1", "10.0.0.5", "192.168.1.9", "169.254.169.254", "::1"):
            with self.subTest(address), self.resolves_to(address):
                with self.assertRaises(ValidationError):
                    assert_public_host("assistant.example")

    def test_one_private_answer_among_public_ones_is_enough_to_refuse(self):
        with self.resolves_to("93.184.216.34", "10.0.0.5"):
            with self.assertRaises(ValidationError):
                assert_public_host("assistant.example")

    def test_an_unresolvable_host_is_refused(self):
        with patch.object(client_module.socket, "getaddrinfo", side_effect=OSError):
            with self.assertRaises(ValidationError):
                assert_public_host("nowhere.invalid")

    def fetch(self, status=200, body=b"{}"):
        response = MagicMock(status_code=status)
        response.raw.read.return_value = body
        with patch.object(client_module, "assert_public_host"), \
                patch.object(client_module.requests, "get", return_value=response) as get:
            result = self.env["plm.mcp.oauth.client"]._fetch_metadata(URL)
        return result, get

    def test_a_document_is_fetched_without_following_redirects(self):
        result, get = self.fetch(body=b'{"a": 1}')
        self.assertEqual(result, {"a": 1})
        self.assertIs(get.call_args.kwargs["allow_redirects"], False)
        self.assertTrue(get.call_args.kwargs["timeout"])

    def test_a_redirect_answer_is_not_a_document(self):
        with self.assertRaises(ValidationError):
            self.fetch(status=302)

    def test_an_oversized_document_is_refused(self):
        with self.assertRaises(ValidationError):
            self.fetch(body=b" " * (client_module.CIMD_MAX_BYTES + 1))

    def test_the_default_list_names_the_known_assistants(self):
        listed = self.env["plm.mcp.oauth.client"]._cimd_allowed_urls()
        self.assertIn("https://claude.ai/oauth/mcp-oauth-client-metadata", listed)

    def test_a_name_from_outside_is_cut_down(self):
        self.assertEqual(clean_name("  My\n  Assistant \t"), "My Assistant")
        self.assertEqual(len(clean_name("x" * 500)), NAME_MAX)
        self.assertEqual(clean_name(None), "")


@tagged("-standard", "odoo_plm_mcp")
class TestMetadataDocuments(OauthHttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_str(PARAM_CIMD, URL)

    # ---------------------------------------------------------------- helpers
    def document(self, **override):
        document = {
            "client_id": URL,
            "client_name": "Listed Assistant",
            "redirect_uris": [REDIRECT],
        }
        document.update(override)
        return document

    def serving(self, document=None, **kwargs):
        """Replace the one method that fetches, with an answer or a failure."""
        return patch.object(
            type(self.env["plm.mcp.oauth.client"]), "_fetch_metadata",
            return_value=document, **kwargs)

    def resolve(self, client_id=URL, **kwargs):
        with self.serving(**kwargs) as fetch:
            return self.env["plm.mcp.oauth.client"]._resolve(client_id), fetch

    # --------------------------------------------------------------- resolving
    def test_a_listed_address_resolves_to_the_client_it_describes(self):
        client, _fetch = self.resolve(document=self.document())
        self.assertEqual(client["client_id"], URL)
        self.assertEqual(client["name"], "Listed Assistant")
        self.assertEqual(client["redirect_uris"], [REDIRECT])
        self.assertFalse(client["id"])

    def test_an_address_that_is_not_listed_is_never_fetched(self):
        client, fetch = self.resolve(
            client_id="https://other.example/client.json", document=self.document())
        self.assertIsNone(client)
        fetch.assert_not_called()

    def test_a_document_must_describe_the_address_it_was_served_from(self):
        client, _fetch = self.resolve(document=self.document(client_id="https://x.example/c"))
        self.assertIsNone(client)

    def test_a_document_with_an_unsafe_redirect_is_refused(self):
        client, _fetch = self.resolve(
            document=self.document(redirect_uris=["http://evil.example/cb"]))
        self.assertIsNone(client)

    def test_a_document_asking_for_a_secret_is_refused(self):
        client, _fetch = self.resolve(
            document=self.document(token_endpoint_auth_method="client_secret_basic"))
        self.assertIsNone(client)

    def test_a_document_that_is_not_an_object_is_refused(self):
        client, _fetch = self.resolve(document=["not", "an", "object"])
        self.assertIsNone(client)

    def test_a_failed_fetch_leaves_the_client_unknown(self):
        failures = (ValidationError("refused"), requests.ConnectionError("down"),
                    ValueError("not json"))
        for failure in failures:
            with self.subTest(type(failure).__name__):
                client, _fetch = self.resolve(side_effect=failure)
                self.assertIsNone(client)

    def test_a_missing_name_falls_back_to_the_host(self):
        client, _fetch = self.resolve(document=self.document(client_name=""))
        self.assertEqual(client["name"], "assistant.example")

    def test_the_document_claude_ai_publishes_is_accepted(self):
        """The shape served at claude.ai/oauth/mcp-oauth-client-metadata."""
        claude = "https://claude.ai/oauth/mcp-oauth-client-metadata"
        self.env["ir.config_parameter"].sudo().set_str(PARAM_CIMD, claude)
        document = {
            "client_id": claude,
            "client_name": "Claude",
            "client_uri": "https://claude.ai",
            "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }
        client, _fetch = self.resolve(client_id=claude, document=document)
        self.assertEqual(client["name"], "Claude")
        self.assertEqual(client["redirect_uris"],
                         ["https://claude.ai/api/mcp/auth_callback"])

    # ------------------------------------------------------------- the whole
    def test_a_listed_application_goes_through_the_whole_flow(self):
        with self.serving(self.document()):
            self.login()
            page = self.consent_page(client_id=URL)
            self.assertEqual(page.status_code, 200)
            self.assertIn("Listed Assistant", page.text)

            response = self.submit(client_id=URL)
            self.assertEqual(response.status_code, 303)
            token = self.exchange(self.code_from(response), client_id=URL)

        self.assertEqual(token.status_code, 200)
        key = self.env["plm.mcp.key"].search([("name", "=", "Listed Assistant (OAuth)")])
        self.assertEqual(key.user_id, self.user)
        self.assertEqual(self.ping(token.json()["access_token"]).status_code, 200)

    def test_an_unlisted_application_cannot_even_reach_the_consent_page(self):
        self.login()
        with self.serving(self.document()):
            response = self.consent_page(client_id="https://other.example/client.json")
        self.assertEqual(response.status_code, 401)

    def test_the_server_says_it_understands_metadata_addresses(self):
        server = self.url_open("/.well-known/oauth-authorization-server/plm/oauth").json()
        self.assertTrue(server["client_id_metadata_document_supported"])


@tagged("-standard", "odoo_plm_mcp")
class TestSelfRegistration(OauthHttpCase):

    def enable(self, on=True):
        self.env["ir.config_parameter"].sudo().set_bool(PARAM_DCR, on)

    def register(self, body=None, raw=None):
        data = raw if raw is not None else json.dumps(
            {"client_name": "Self-registered", "redirect_uris": [REDIRECT]}
            if body is None else body)
        return self.url_open(
            REGISTER, data=data, headers={"Content-Type": "application/json"})

    def registered(self):
        return self.env["plm.mcp.oauth.client"].search([("source", "=", "registered")])

    # ------------------------------------------------------------------ gate
    def test_registration_is_off_by_default(self):
        response = self.register()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.registered())

    def test_the_endpoint_is_advertised_only_when_it_is_on(self):
        path = "/.well-known/oauth-authorization-server/plm/oauth"
        self.assertNotIn("registration_endpoint", self.url_open(path).json())
        self.enable()
        self.assertTrue(self.url_open(path).json()["registration_endpoint"].endswith(REGISTER))

    # ----------------------------------------------------------- registering
    def test_an_application_can_register_and_then_connect(self):
        self.enable()
        response = self.register()
        self.assertEqual(response.status_code, 201)
        answer = response.json()
        self.assertEqual(answer["token_endpoint_auth_method"], "none")
        self.assertEqual(answer["redirect_uris"], [REDIRECT])

        client = self.registered()
        self.assertEqual(client.client_id, answer["client_id"])
        self.assertFalse(client.last_used_on)

        self.login()
        page = self.consent_page(client_id=answer["client_id"])
        self.assertEqual(page.status_code, 200)
        self.assertIn("Self-registered", page.text)

        code = self.code_from(self.submit(client_id=answer["client_id"]))
        token = self.exchange(code, client_id=answer["client_id"])
        self.assertEqual(token.status_code, 200)
        client.invalidate_recordset()
        self.assertTrue(client.last_used_on)

    def test_a_bad_registration_is_refused_and_leaves_nothing_behind(self):
        self.enable()
        cases = {
            "unsafe redirect": ({"redirect_uris": ["http://evil.example/cb"]},
                                "invalid_redirect_uri"),
            "no redirect": ({"client_name": "x"}, "invalid_redirect_uri"),
            "empty redirect list": ({"redirect_uris": []}, "invalid_redirect_uri"),
            "redirect not a list": ({"redirect_uris": REDIRECT}, "invalid_redirect_uri"),
            "a secret": ({"redirect_uris": [REDIRECT],
                          "token_endpoint_auth_method": "client_secret_basic"},
                         "invalid_client_metadata"),
        }
        for label, (body, error) in cases.items():
            with self.subTest(label):
                response = self.register(body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], error)
        self.assertFalse(self.registered())

    def test_a_body_that_is_not_json_is_refused(self):
        self.enable()
        response = self.register(raw="not json at all")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_client_metadata")

    def test_registration_stops_when_too_many_wait_unused(self):
        self.enable()
        with patch.object(client_module, "MAX_UNUSED_REGISTERED", 1):
            self.assertEqual(self.register().status_code, 201)
            second = self.register()
        self.assertEqual(second.status_code, 429)
        self.assertEqual(len(self.registered()), 1)

    def test_a_long_name_is_cut_down(self):
        self.enable()
        self.register({"client_name": "x" * 500, "redirect_uris": [REDIRECT]})
        self.assertEqual(len(self.registered().name), NAME_MAX)

    # ---------------------------------------------------------------- clean-up
    def test_the_clean_up_removes_only_old_unused_registered_clients(self):
        clients = self.env["plm.mcp.oauth.client"]
        old = fields.Datetime.now() - timedelta(days=client_module.UNUSED_RETENTION_DAYS + 1)

        def make(source, used=False, old_enough=True):
            client = clients.create({
                "name": "%s %s" % (source, used), "redirect_uris": REDIRECT})
            client.write({"source": source})
            if used:
                client.last_used_on = fields.Datetime.now()
            if old_enough:
                self.env.cr.execute(
                    "UPDATE plm_mcp_oauth_client SET create_date = %s WHERE id = %s",
                    (old, client.id))
            return client

        stale = make("registered")
        used = make("registered", used=True)
        recent = make("registered", old_enough=False)
        manual = make("manual")
        clients.invalidate_model()

        clients._gc_unused_registered_clients()

        self.assertFalse(stale.exists())
        self.assertTrue(used.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(manual.exists())
