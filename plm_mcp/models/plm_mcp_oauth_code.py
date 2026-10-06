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
"""The short-lived code that is traded for a token.

When a person allows an application, the browser is sent back to it carrying a
code, and the application then exchanges that code for a token on its own, out
of the browser's sight. The code is the only thing that crosses the browser, so
it is made worthless quickly and to anyone but its owner:

- it lives two minutes;
- it is stored as a digest, like the keys, so reading the table gives nothing;
- it works once — it is deleted the moment it is presented, whatever follows;
- it is bound to the application, the redirect address and a PKCE challenge, so
  a code intercepted on the way back cannot be used without the verifier that
  only the application holds.

A failed exchange is returned, never raised. Raising would roll the transaction
back and with it the deletion of the code, which would leave a wrongly
presented code usable a second time.
"""
import base64
import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from odoo import _, api, fields, models

from .plm_mcp_key import _digest

CODE_TTL_SECONDS = 120
CODE_BYTES = 32

# RFC 7636: both the verifier and the S256 challenge are 43 to 128 characters
# of the unreserved set.
PKCE_VALUE = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")


def valid_pkce_value(value):
    return bool(value) and bool(PKCE_VALUE.match(value))


def verifier_matches_challenge(verifier, challenge):
    """S256: the challenge is the base64url of the SHA-256 of the verifier."""
    if not valid_pkce_value(verifier) or not valid_pkce_value(challenge):
        return False
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, challenge)


def _failure(error, description):
    return {"error": error, "error_description": description}


class PlmMcpOauthCode(models.Model):
    _name = "plm.mcp.oauth.code"
    _description = "PLM MCP OAuth Authorization Code"

    code_digest = fields.Char(required=True, index=True, readonly=True)
    client_id = fields.Char(required=True, readonly=True)
    redirect_uri = fields.Char(required=True, readonly=True)
    code_challenge = fields.Char(required=True, readonly=True)
    user_id = fields.Many2one(
        "res.users", required=True, ondelete="cascade", readonly=True)
    key_days = fields.Integer(
        readonly=True,
        help="How many days the token will live; 0 means it does not expire.",
    )
    expires_at = fields.Datetime(required=True, readonly=True)

    _code_digest_uniq = models.Constraint(
        "unique (code_digest)",
        "That code already exists.",
    )

    # ------------------------------------------------------------------ issue
    @api.model
    def _issue(self, client_id, redirect_uri, code_challenge, user, key_days):
        """Create a code and return it. Only its digest is kept."""
        code = secrets.token_urlsafe(CODE_BYTES)
        self.sudo().create({
            "code_digest": _digest(code),
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "user_id": user.id,
            "key_days": key_days,
            "expires_at": fields.Datetime.now()
            + timedelta(seconds=CODE_TTL_SECONDS),
        })
        return code

    # ----------------------------------------------------------------- redeem
    @api.model
    def _redeem(self, code, client, redirect_uri, code_verifier):
        """Trade a code for a token.

        :param client: what ``plm.mcp.oauth.client._resolve`` returned
        :return: ``{"access_token", ...}`` on success, otherwise
            ``{"error", "error_description"}`` — never an exception, see above.
        """
        record = self.sudo().search(
            [("code_digest", "=", _digest(code or ""))], limit=1)
        if not record:
            return _failure("invalid_grant", _("Invalid authorization code."))

        # Spent from this point on, whatever the outcome.
        issued = {
            "client_id": record.client_id,
            "redirect_uri": record.redirect_uri,
            "code_challenge": record.code_challenge,
            "user": record.user_id,
            "key_days": record.key_days,
            "expires_at": record.expires_at,
        }
        record.unlink()

        if issued["expires_at"] < fields.Datetime.now():
            return _failure("invalid_grant", _("The authorization code expired."))
        if issued["client_id"] != client["client_id"]:
            return _failure("invalid_grant", _("The code was issued to another client."))
        if issued["redirect_uri"] != redirect_uri:
            return _failure("invalid_grant", _("The redirect address does not match."))
        if not verifier_matches_challenge(code_verifier, issued["code_challenge"]):
            return _failure("invalid_grant", _("Invalid PKCE code_verifier."))

        user = issued["user"]
        if not user.active or not user._is_internal():
            return _failure("invalid_grant", _("The user may not use this service."))
        token = self._issue_token(user, client["name"], issued["key_days"])
        self.env["plm.mcp.oauth.client"]._mark_used(client)
        return token

    @api.model
    def _issue_token(self, user, client_name, key_days):
        """A plm.mcp.key for the user, named after the application."""
        values = {
            "name": _("%s (OAuth)", client_name),
            "user_id": user.id,
        }
        if key_days:
            values["expires_on"] = fields.Date.today() + timedelta(days=key_days)
        key = self.env["plm.mcp.key"].sudo().create(values)

        result = {
            "access_token": key.key_clear,
            "token_type": "Bearer",
            "scope": "mcp",
        }
        if key_days:
            result["expires_in"] = key_days * 86400
        return result

    # -------------------------------------------------------------------- gc
    @api.autovacuum
    def _gc_expired_codes(self):
        self.sudo().search([("expires_at", "<", fields.Datetime.now())]).unlink()
