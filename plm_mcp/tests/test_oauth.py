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
"""The OAuth flow, walked the way an AI application walks it.

    odoo --test-tags=odoo_plm_mcp -u plm_mcp -d <database>

The HTTP tests go through the real routes — the login redirect, the consent
page, the CSRF token, the code on the way back, the exchange — because the
mistakes that matter in an authorization server are in how the steps fit
together, not in any one of them.
"""
import base64
import hashlib
import json
import re
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase
from odoo.tools import mute_logger

from odoo.addons.plm_mcp.models.plm_mcp_oauth_client import (
    check_redirect_uri,
    redirect_uri_registered,
)
from odoo.addons.plm_mcp.models.plm_mcp_oauth_code import (
    verifier_matches_challenge,
)

AUTHORIZE = "/plm/oauth/authorize"
SUBMIT = "/plm/oauth/authorize/submit"
TOKEN = "/plm/oauth/token"
REVOKE = "/plm/oauth/revoke"
MCP = "/plm/mcp"

REDIRECT = "https://client.example/callback"
VERIFIER = "v" * 64


def challenge_of(verifier):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


CHALLENGE = challenge_of(VERIFIER)


@tagged("-standard", "odoo_plm_mcp")
class TestOauthRules(TransactionCase):
    """The checks the flow rests on, without the HTTP around them."""

    def test_https_redirect_is_acceptable(self):
        check_redirect_uri("https://client.example/callback")

    def test_http_is_acceptable_on_loopback_only(self):
        check_redirect_uri("http://localhost:8123/cb")
        check_redirect_uri("http://127.0.0.1/cb")
        with self.assertRaises(ValidationError):
            check_redirect_uri("http://client.example/callback")

    def test_a_fragment_or_credentials_are_refused(self):
        with self.assertRaises(ValidationError):
            check_redirect_uri("https://client.example/cb#frag")
        with self.assertRaises(ValidationError):
            check_redirect_uri("https://user:pw@client.example/cb")

    def test_a_client_cannot_be_saved_with_a_bad_redirect(self):
        with self.assertRaises(ValidationError):
            self.env["plm.mcp.oauth.client"].create({
                "name": "Bad", "redirect_uris": "http://client.example/cb"})

    def test_redirect_match_is_exact(self):
        registered = [REDIRECT]
        self.assertTrue(redirect_uri_registered(REDIRECT, registered))
        self.assertFalse(redirect_uri_registered(REDIRECT + "/", registered))
        self.assertFalse(redirect_uri_registered(
            "https://client.example/callback?x=1", registered))
        self.assertFalse(redirect_uri_registered(
            "https://evil.example/callback", registered))

    def test_a_loopback_port_may_differ(self):
        """The port is picked by the application each time it starts."""
        registered = ["http://localhost/cb"]
        self.assertTrue(redirect_uri_registered("http://localhost:5555/cb", registered))
        self.assertFalse(redirect_uri_registered("http://localhost:5555/other", registered))
        self.assertFalse(redirect_uri_registered("http://127.0.0.1:5555/cb", registered))

    def test_pkce(self):
        self.assertTrue(verifier_matches_challenge(VERIFIER, CHALLENGE))
        self.assertFalse(verifier_matches_challenge("w" * 64, CHALLENGE))
        self.assertFalse(verifier_matches_challenge("short", challenge_of("short")))
        self.assertFalse(verifier_matches_challenge(None, CHALLENGE))


class OauthHttpCase(HttpCase):
    """The users, a client and the steps of the flow; the tests are elsewhere."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create({
            "name": "OAuth user",
            "login": "oauth_user",
            "password": "oauth_user_pw_2026",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.portal = cls.env["res.users"].create({
            "name": "OAuth portal",
            "login": "oauth_portal",
            "password": "oauth_portal_pw_2026",
            "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
        })
        cls.client_rec = cls.env["plm.mcp.oauth.client"].create({
            "name": "Test Assistant",
            "redirect_uris": REDIRECT,
        })
        cls.base = cls.env["ir.config_parameter"].sudo().get_str(
            "web.base.url").rstrip("/")

    # ---------------------------------------------------------------- helpers
    def login(self):
        self.authenticate("oauth_user", "oauth_user_pw_2026")

    def authorize_params(self, **extra):
        params = {
            "client_id": self.client_rec.client_id,
            "redirect_uri": REDIRECT,
            "response_type": "code",
            "code_challenge": CHALLENGE,
            "code_challenge_method": "S256",
            "state": "xyz",
        }
        params.update(extra)
        return params

    def consent_page(self, **extra):
        return self.url_open(AUTHORIZE, params=self.authorize_params(**extra))

    def submit(self, allow="true", duration="1", csrf=True, **extra):
        data = self.authorize_params(**extra)
        data.update(allow=allow, duration=duration)
        if csrf:
            tag = re.search(
                r'<input[^>]*name="csrf_token"[^>]*>', self.consent_page().text).group(0)
            data["csrf_token"] = re.search(r'value="([^"]+)"', tag).group(1)
        return self.url_open(SUBMIT, data=data, allow_redirects=False)

    def code_from(self, response):
        location = response.headers["Location"]
        return parse_qs(urlsplit(location).query)["code"][0]

    def get_code(self, **extra):
        self.login()
        response = self.submit(**extra)
        self.assertEqual(response.status_code, 303)
        return self.code_from(response)

    def exchange(self, code, **extra):
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_rec.client_id,
            "code": code,
            "redirect_uri": REDIRECT,
            "code_verifier": VERIFIER,
        }
        data.update(extra)
        return self.url_open(TOKEN, data=data)

    def ping(self, token):
        return self.url_open(
            MCP, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer %s" % token})


@tagged("-standard", "odoo_plm_mcp")
class TestOauthFlow(OauthHttpCase):

    # -------------------------------------------------------------- discovery
    def test_the_discovery_documents_name_the_endpoints(self):
        resource = self.url_open(
            "/.well-known/oauth-protected-resource/plm/mcp").json()
        self.assertEqual(resource["resource"], self.base + "/plm/mcp")
        self.assertEqual(resource["authorization_servers"], [self.base + "/plm/oauth"])

        server = self.url_open(
            "/.well-known/oauth-authorization-server/plm/oauth").json()
        self.assertEqual(server["issuer"], self.base + "/plm/oauth")
        self.assertEqual(server["authorization_endpoint"], self.base + AUTHORIZE)
        self.assertEqual(server["token_endpoint"], self.base + TOKEN)
        self.assertEqual(server["revocation_endpoint"], self.base + REVOKE)
        self.assertEqual(server["code_challenge_methods_supported"], ["S256"])

    @mute_logger("odoo.http")
    def test_the_401_points_at_the_login_flow(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        headers = {"Content-Type": "application/json"}
        response = self.url_open(MCP, data=body, headers=headers)
        self.assertEqual(response.status_code, 401)
        challenge = response.headers["WWW-Authenticate"]
        self.assertIn(
            'resource_metadata="%s/.well-known/oauth-protected-resource/plm/mcp"'
            % self.base, challenge)
        self.assertNotIn("invalid_token", challenge)

        headers["Authorization"] = "Bearer not-a-token"
        response = self.url_open(MCP, data=body, headers=headers)
        self.assertIn('error="invalid_token"', response.headers["WWW-Authenticate"])

    # -------------------------------------------------------------- authorize
    def test_authorize_sends_an_anonymous_visitor_to_the_login(self):
        response = self.url_open(
            AUTHORIZE, params=self.authorize_params(), allow_redirects=False)
        self.assertIn(response.status_code, (302, 303))
        self.assertIn("/web/login", response.headers["Location"])

    def test_the_consent_page_names_the_application(self):
        self.login()
        response = self.consent_page()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test Assistant", response.text)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_a_bad_request_is_answered_with_an_error_not_a_redirect(self):
        self.login()
        cases = {
            "unknown client": ({"client_id": "nobody"}, 401, "Application not recognised"),
            "unregistered redirect": (
                {"redirect_uri": "https://evil.example/cb"}, 400, "Redirect address not allowed"),
            "plain PKCE": ({"code_challenge_method": "plain"}, 400, "Invalid request"),
            "no challenge": ({"code_challenge": ""}, 400, "Invalid request"),
            "implicit flow": ({"response_type": "token"}, 400, "Invalid request"),
        }
        for label, (extra, status, heading) in cases.items():
            with self.subTest(label):
                response = self.url_open(
                    AUTHORIZE, params=self.authorize_params(**extra),
                    allow_redirects=False)
                self.assertEqual(response.status_code, status)
                self.assertNotIn("Location", response.headers)
                self.assertIn(heading, response.text)

    def test_the_error_page_shows_the_address_asked_for_and_escapes_it(self):
        """The one administrators need to see, and the one an attacker controls."""
        self.login()
        response = self.consent_page(redirect_uri="https://evil.example/<b>x</b>")
        self.assertEqual(response.status_code, 400)
        self.assertIn("evil.example", response.text)
        self.assertIn("&lt;b&gt;", response.text)
        self.assertNotIn("<b>x</b>", response.text)

    def test_an_archived_client_is_unknown(self):
        self.client_rec.active = False
        self.login()
        self.assertEqual(self.consent_page().status_code, 401)

    def test_a_portal_user_may_not_connect_an_application(self):
        self.authenticate("oauth_portal", "oauth_portal_pw_2026")
        response = self.consent_page()
        self.assertEqual(response.status_code, 403)
        self.assertIn("Only internal Odoo users", response.text)

    @mute_logger("odoo.http")
    def test_submit_without_a_csrf_token_is_refused(self):
        self.login()
        response = self.submit(csrf=False)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.env["plm.mcp.oauth.code"].search([]))

    def test_deny_goes_back_with_access_denied(self):
        self.login()
        response = self.submit(allow="false")
        self.assertEqual(response.status_code, 303)
        query = parse_qs(urlsplit(response.headers["Location"]).query)
        self.assertEqual(query["error"], ["access_denied"])
        self.assertEqual(query["state"], ["xyz"])
        self.assertFalse(self.env["plm.mcp.oauth.code"].search([]))

    def test_a_duration_that_was_not_offered_is_refused(self):
        self.login()
        response = self.submit(duration="9999")
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------- the whole
    def test_the_whole_flow_gives_a_working_key(self):
        self.login()
        response = self.submit(duration="1")
        self.assertEqual(response.status_code, 303)
        location = response.headers["Location"]
        self.assertTrue(location.startswith(REDIRECT + "?"))
        query = parse_qs(urlsplit(location).query)
        self.assertEqual(query["state"], ["xyz"])
        self.assertEqual(query["iss"], [self.base + "/plm/oauth"])

        token_response = self.exchange(query["code"][0])
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(token_response.headers["Cache-Control"], "no-store")
        token = token_response.json()
        self.assertEqual(token["token_type"], "Bearer")
        self.assertEqual(token["expires_in"], 86400)

        key = self.env["plm.mcp.key"].search([("name", "=", "Test Assistant (OAuth)")])
        self.assertEqual(key.user_id, self.user)
        self.assertEqual(key.expires_on, fields.Date.today() + timedelta(days=1))
        self.assertEqual(self.ping(token["access_token"]).status_code, 200)

    # ------------------------------------------------------------------ token
    def test_a_code_works_once(self):
        code = self.get_code()
        self.assertEqual(self.exchange(code).status_code, 200)
        again = self.exchange(code)
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()["error"], "invalid_grant")

    def test_a_wrong_verifier_spends_the_code(self):
        """Guessing the verifier must not leave the code to try again."""
        code = self.get_code()
        self.assertEqual(self.exchange(code, code_verifier="w" * 64).status_code, 400)
        self.assertEqual(self.exchange(code).status_code, 400)
        self.assertFalse(self.env["plm.mcp.key"].search(
            [("name", "=", "Test Assistant (OAuth)")]))

    def test_a_wrong_redirect_at_the_exchange_is_refused(self):
        code = self.get_code()
        response = self.exchange(code, redirect_uri="https://client.example/other")
        self.assertEqual(response.status_code, 400)

    def test_a_code_belongs_to_the_client_it_was_issued_to(self):
        other = self.env["plm.mcp.oauth.client"].create({
            "name": "Other", "redirect_uris": REDIRECT})
        code = self.get_code()
        response = self.exchange(code, client_id=other.client_id)
        self.assertEqual(response.status_code, 400)

    def test_an_expired_code_is_refused(self):
        code = self.get_code()
        self.env["plm.mcp.oauth.code"].sudo().search([]).write({
            "expires_at": fields.Datetime.now() - timedelta(seconds=1)})
        self.assertEqual(self.exchange(code).status_code, 400)

    def test_an_unknown_client_cannot_exchange(self):
        code = self.get_code()
        response = self.exchange(code, client_id="nobody")
        self.assertEqual(response.status_code, 401)

    def test_only_the_authorization_code_grant_exists(self):
        response = self.exchange("x", grant_type="password")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "unsupported_grant_type")

    # ----------------------------------------------------------------- revoke
    @mute_logger("odoo.http")
    def test_revoking_a_token_switches_the_key_off(self):
        token = self.exchange(self.get_code()).json()["access_token"]
        self.assertEqual(self.ping(token).status_code, 200)

        response = self.url_open(REVOKE, data={"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ping(token).status_code, 401)

    def test_revoking_an_unknown_token_is_not_an_error(self):
        response = self.url_open(REVOKE, data={"token": "unknown"})
        self.assertEqual(response.status_code, 200)
