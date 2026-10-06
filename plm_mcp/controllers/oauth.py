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
"""Letting an AI application ask for a token itself.

Without this, connecting an application means a person creates a key, copies it
and pastes it into the client. Most hosted assistants do not offer a field for
that; they expect to be sent to a login page and handed a token afterwards,
which is OAuth 2.1 with PKCE. The flow, in the order it happens:

1. the application reads the two ``.well-known`` documents and learns where to
   send the person;
2. ``/plm/oauth/authorize`` — the person logs in to Odoo as usual and sees who
   is asking;
3. on Allow, the browser goes back to the application with a one-time code;
4. ``/plm/oauth/token`` — the application trades the code, with the PKCE
   verifier only it knows, for a token. The token is a plm.mcp.key, the same
   thing a person would have created by hand, so it is managed in one place.

Everything lives under ``/plm/`` so it can never collide with the OAuth server
of Odoo's own ai_mcp, should a database have both. Nothing here reads the host
name from the request: the addresses given out come from ``web.base.url``,
which an administrator sets, because a host header is chosen by the caller.
"""
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

from ..models.plm_mcp_key import _digest
from ..models.plm_mcp_oauth_client import redirect_uri_registered
from ..models.plm_mcp_oauth_code import valid_pkce_value

_logger = logging.getLogger(__name__)

RESOURCE_PATH = "/plm/mcp"
ISSUER_PATH = "/plm/oauth"
PROTECTED_RESOURCE_METADATA_PATH = "/.well-known/oauth-protected-resource" + RESOURCE_PATH
AUTHORIZATION_SERVER_METADATA_PATH = "/.well-known/oauth-authorization-server" + ISSUER_PATH

NO_STORE = [("Cache-Control", "no-store"), ("Pragma", "no-cache")]


def base_url():
    """The address this server is reached at, as an administrator set it."""
    return request.env["ir.config_parameter"].sudo().get_str(
        "web.base.url").rstrip("/")


def protected_resource_metadata_url():
    return base_url() + PROTECTED_RESOURCE_METADATA_PATH


def merge_params(url, params):
    """``url`` with the non-empty ``params`` added to its query string."""
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query += [(k, v) for k, v in params.items() if v]
    return urlunsplit(parts._replace(query=urlencode(query)))


def oauth_error(error, description=None, status=400):
    """A JSON error. Returned, not raised: see plm_mcp_oauth_code."""
    body = {"error": error}
    if description:
        body["error_description"] = description
    return request.make_json_response(body, status=status, headers=NO_STORE)


def error_page(title, message, detail=None, hint=None, status=400):
    """A readable error for the pages a person sees in the browser.

    The authorize and submit steps are opened by a person, not read by a
    program: a bare JSON body tells them nothing about what to do. The status
    code is kept, so a client or a test still reads it. The token, revoke and
    registration endpoints are called by programs and keep answering in JSON.

    ``detail`` is text that came from outside — the redirect address an
    application asked for — and is escaped when shown, as everything is.
    """
    response = request.render("plm_mcp.oauth_error", {
        "title": title,
        "message": message,
        "detail": detail,
        "hint": hint,
    })
    response.status_code = status
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    for header, value in NO_STORE:
        response.headers[header] = value
    return response


class PlmMcpOauth(Controller):

    # -------------------------------------------------------------- discovery
    @route(PROTECTED_RESOURCE_METADATA_PATH, type="http", auth="public",
           methods=["GET"], cors="*", save_session=False)
    def protected_resource_metadata(self):
        """RFC 9728: which server decides who may use the MCP endpoint."""
        root = base_url()
        return request.make_json_response({
            "resource": root + RESOURCE_PATH,
            "authorization_servers": [root + ISSUER_PATH],
        })

    @route(AUTHORIZATION_SERVER_METADATA_PATH, type="http", auth="public",
           methods=["GET"], cors="*", save_session=False)
    def authorization_server_metadata(self):
        """RFC 8414: where the application sends the person and the code."""
        root = base_url() + ISSUER_PATH
        metadata = {
            "issuer": root,
            "authorization_endpoint": root + "/authorize",
            "token_endpoint": root + "/token",
            "revocation_endpoint": root + "/revoke",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["mcp"],
            "authorization_response_iss_parameter_supported": True,
            # An application may use the address of its own metadata document
            # as its client ID (only the ones listed in the settings are served).
            "client_id_metadata_document_supported": True,
        }
        # Offered only when an administrator switched it on: an application
        # that finds no registration endpoint goes by its metadata address.
        if request.env["plm.mcp.oauth.client"]._dcr_enabled():
            metadata["registration_endpoint"] = root + "/register"
        return request.make_json_response(metadata)

    # ----------------------------------------------------------- registration
    @route(ISSUER_PATH + "/register", type="http", auth="public",
           methods=["POST"], csrf=False, cors="*", save_session=False)
    def register(self):
        """RFC 7591: an application asks to be known. Off unless switched on.

        It creates a record, but the record grants nothing: a person still has
        to log in and allow it, and sees the name it chose. That is why this is
        off by default and bounded when on.
        """
        clients = request.env["plm.mcp.oauth.client"]
        if not clients._dcr_enabled():
            return oauth_error(
                "access_denied",
                "Dynamic client registration is disabled on this server.",
                status=403)
        try:
            payload = request.get_json_data()
        except Exception:
            payload = None
        if not isinstance(payload, dict):
            return oauth_error("invalid_client_metadata", "The body must be a JSON object.")
        if payload.get("token_endpoint_auth_method", "none") != "none":
            return oauth_error(
                "invalid_client_metadata", "Only token_endpoint_auth_method=none is supported.")
        if not clients._registration_open():
            return oauth_error(
                "temporarily_unavailable",
                "Too many applications are waiting; try again later.", status=429)

        try:
            client = clients._register(
                payload.get("client_name"), payload.get("redirect_uris"))
        except ValidationError as error:
            return oauth_error("invalid_redirect_uri", str(error))
        return request.make_json_response({
            "client_id": client.client_id,
            "client_name": client.name,
            "redirect_uris": client.redirect_uris.splitlines(),
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
        }, status=201, headers=NO_STORE)

    # -------------------------------------------------------------- authorize
    @route(ISSUER_PATH + "/authorize", type="http", auth="user",
           methods=["GET"], save_session=False)
    def authorize(self, **params):
        """The page where the person decides. Needs an Odoo login first."""
        client, problem = self._check_request(params)
        if problem:
            return problem

        durations = request.env["res.users.apikeys.description"]._selection_duration()
        response = request.render("plm_mcp.oauth_consent", {
            "client_name": client["name"],
            "user": request.env.user,
            "params": {key: params.get(key) or "" for key in (
                "client_id", "redirect_uri", "response_type", "code_challenge",
                "code_challenge_method", "state")},
            "durations": durations,
            "default_duration": request.env[
                "res.users.apikeys.description"]._default_duration(),
        })
        # The page must be a top-level navigation, never inside another site's
        # frame: a framed consent page is a button someone else can place under
        # the person's cursor.
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response

    @route(ISSUER_PATH + "/authorize/submit", type="http", auth="user",
           methods=["POST"], save_session=False)
    def submit(self, **params):
        """Allow or Deny. CSRF-protected like any form of Odoo."""
        client, problem = self._check_request(params)
        if problem:
            return problem

        redirect_uri = params["redirect_uri"]
        state = params.get("state") or ""
        if params.get("allow") != "true":
            return request.redirect(merge_params(redirect_uri, {
                "error": "access_denied", "state": state,
            }), local=False)

        durations = dict(
            request.env["res.users.apikeys.description"]._selection_duration())
        duration = params.get("duration")
        if duration not in durations:
            return error_page(
                request.env._("Choose how long access lasts"),
                request.env._("The duration that was sent is not one of the offered ones."),
                hint=request.env._("Go back to the previous page and pick one of the durations offered."))

        code = request.env["plm.mcp.oauth.code"]._issue(
            client_id=client["client_id"],
            redirect_uri=redirect_uri,
            code_challenge=params["code_challenge"],
            user=request.env.user,
            key_days=int(duration),
        )
        return request.redirect(merge_params(redirect_uri, {
            "code": code,
            "state": state,
            # RFC 9207: lets the application check which server answered.
            "iss": base_url() + ISSUER_PATH,
        }), local=False)

    def _check_request(self, params):
        """The client and no problem, or no client and the response to give.

        An unknown client or an unregistered redirect address is answered with
        an error here and never by redirecting: the address is the thing that
        cannot be trusted yet.
        """
        client = request.env["plm.mcp.oauth.client"]._resolve(params.get("client_id"))
        _ = request.env._
        if not client:
            return None, error_page(
                _("Application not recognised"),
                _("This application is not registered with this server."),
                hint=_(
                    "Check the client ID entered in the application. An "
                    "administrator can register it under Configuration → MCP → "
                    "OAuth Clients, or list its metadata address in the PLM settings."),
                status=401)
        redirect_uri = params.get("redirect_uri") or ""
        if not redirect_uri_registered(redirect_uri, client["redirect_uris"]):
            return None, error_page(
                _("Redirect address not allowed"),
                _("The application asked to be sent back to an address that is "
                  "not registered for it."),
                detail=redirect_uri,
                hint=_(
                    "An administrator must add this address to the Redirect URIs "
                    "of the client, under Configuration → MCP → OAuth Clients."))
        if params.get("response_type") != "code" \
                or params.get("code_challenge_method") != "S256" \
                or not valid_pkce_value(params.get("code_challenge")):
            return None, error_page(
                _("Invalid request"),
                _("The application sent a request this server cannot accept: it "
                  "must use the authorization code flow with PKCE (S256)."),
                hint=_("Update the application, or contact its vendor."))

        user = request.env.user
        if not user.active or not user._is_internal():
            return None, error_page(
                _("Access not allowed"),
                _("Only internal Odoo users can connect an application."),
                hint=_("Log in with an internal user and try again."),
                status=403)
        return client, None

    # ------------------------------------------------------------------ token
    @route(ISSUER_PATH + "/token", type="http", auth="public", methods=["POST"],
           csrf=False, cors="*", save_session=False)
    def token(self, **params):
        """Trade the code for a token."""
        if params.get("grant_type") != "authorization_code":
            return oauth_error("unsupported_grant_type")
        client = request.env["plm.mcp.oauth.client"]._resolve(params.get("client_id"))
        if not client:
            return oauth_error("invalid_client", "Unknown client.", status=401)

        result = request.env["plm.mcp.oauth.code"]._redeem(
            code=params.get("code"),
            client=client,
            redirect_uri=params.get("redirect_uri"),
            code_verifier=params.get("code_verifier"),
        )
        if "error" in result:
            _logger.info("plm_mcp: token refused for %s: %s",
                         client["name"], result["error_description"])
            return oauth_error(result["error"], result["error_description"])
        return request.make_json_response(result, headers=NO_STORE)

    # ----------------------------------------------------------------- revoke
    @route(ISSUER_PATH + "/revoke", type="http", auth="public", methods=["POST"],
           csrf=False, cors="*", save_session=False)
    def revoke(self, **params):
        """Switch a token off. Always answers 200, as RFC 7009 asks.

        Whoever holds the token may revoke it, which is the point: a leaked
        token can be cut off by whoever finds it.
        """
        token = params.get("token")
        if token:
            key = request.env["plm.mcp.key"].sudo().search(
                [("key_digest", "=", _digest(token))], limit=1)
            if key:
                key.active = False
                _logger.info("plm_mcp: token of key %s revoked", key.name)
        return request.make_json_response({}, headers=NO_STORE)
