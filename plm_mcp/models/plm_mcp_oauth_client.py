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
"""The AI applications allowed to ask for a token through OAuth.

An application that wants a token must first be known: its name is what the
person sees on the consent page, and its redirect addresses are the only places
the authorization code may be sent. A code sent anywhere else would be a code
handed to a stranger, so the redirect check is the part of the flow that
matters most and is kept exact.

There are three ways an application becomes known, and ``_resolve`` is the only
door they all go through, so nothing around it cares which one was used:

- an administrator creates it by hand (a record of this model);
- it names itself by a metadata address — its client ID *is* an https address,
  and the document found there gives its name and redirect addresses (CIMD).
  Only addresses an administrator listed are ever fetched, which is both the
  trust decision and the main defence against being made to fetch something
  else;
- it registers itself (DCR), when an administrator has switched that on. That
  leaves a record behind, flagged as registered, and the ones that never got a
  token are cleaned up.
"""
import ipaddress
import json
import logging
import socket
import uuid
from datetime import timedelta
from urllib.parse import urlsplit

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Where a native or desktop application listens for the redirect. RFC 8252 lets
# these use plain http, since the traffic never leaves the machine.
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")

# Settings (system parameters), prefixed so they cannot meet the ones Odoo's own
# ai_mcp keeps under bare names.
PARAM_DCR = "plm_mcp.oauth_enable_dcr"
PARAM_CIMD = "plm_mcp.oauth_cimd_urls"

CIMD_TIMEOUT = 5
CIMD_MAX_BYTES = 64 * 1024
NAME_MAX = 64
MAX_REDIRECT_URIS = 10
# Registration is open to anyone when it is on, so it is bounded: this many
# registered applications that never got a token, and no more are accepted.
MAX_UNUSED_REGISTERED = 100
UNUSED_RETENTION_DAYS = 30


def split_uris(text):
    """The addresses of a multi-line field, one per line, blanks dropped."""
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def clean_name(value):
    """A name fit to show and to store: one line, bounded.

    It comes from outside — a metadata document, a registration request — so it
    is cut down before it goes anywhere. It is still escaped wherever it is
    displayed; this only keeps it from being absurd.
    """
    return " ".join(str(value or "").split())[:NAME_MAX]


def check_redirect_uri(uri):
    """Raise unless ``uri`` is an address a code may safely be sent to.

    https anywhere, or http on the loopback interface only; never a fragment,
    never credentials in the address.
    """
    parts = urlsplit(uri)
    host = parts.hostname
    valid = bool(host) and not parts.fragment and not parts.username \
        and not parts.password
    if valid and parts.scheme == "https":
        return
    if valid and parts.scheme == "http" and host in LOOPBACK_HOSTS:
        return
    raise ValidationError(_(
        "%s is not an acceptable redirect address: it must be https, or http "
        "on localhost, with no fragment and no credentials.", uri))


def check_redirect_uris(uris):
    """Raise unless ``uris`` is a usable list of redirect addresses."""
    if not isinstance(uris, list) or not uris or len(uris) > MAX_REDIRECT_URIS \
            or not all(isinstance(uri, str) and uri for uri in uris):
        raise ValidationError(_("Give between 1 and %s redirect addresses.",
                                MAX_REDIRECT_URIS))
    for uri in uris:
        check_redirect_uri(uri)


def _loopback_key(uri):
    """What identifies a loopback address when its port is left out."""
    parts = urlsplit(uri)
    if parts.scheme == "http" and parts.hostname in LOOPBACK_HOSTS:
        return (parts.scheme, parts.hostname, parts.path, parts.query)
    return None


def redirect_uri_registered(requested, registered):
    """Whether ``requested`` is one of the registered addresses.

    Exact match. The one exception is a loopback address, whose port is chosen
    by the application each time it starts and so cannot be registered in
    advance (RFC 8252, section 7.3).
    """
    if requested in registered:
        return True
    key = _loopback_key(requested)
    return bool(key) and any(_loopback_key(uri) == key for uri in registered)


def assert_public_host(host):
    """Raise unless every address ``host`` resolves to is a public one.

    The list of fetchable addresses is the real control; this is the second
    line, so a listed name that is made to point inside the network still
    cannot be used to reach it.
    """
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        raise ValidationError(_("The host %s cannot be resolved.", host))
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValidationError(_("The host %s is not a public address.", host))


class PlmMcpOauthClient(models.Model):
    _name = "plm.mcp.oauth.client"
    _description = "PLM MCP OAuth Client"
    _order = "name"

    name = fields.Char(
        required=True,
        help="Shown to the person on the consent page: the application "
             "asking for access.",
    )
    client_id = fields.Char(
        required=True, copy=False, readonly=True, index=True,
        default=lambda self: uuid.uuid4().hex,
        help="What the application sends to say who it is. Not a secret.",
    )
    redirect_uris = fields.Text(
        required=True,
        help="One address per line. The authorization code is sent only to "
             "one of these: https, or http on localhost.",
    )
    active = fields.Boolean(
        default=True,
        help="Archiving a client stops it getting any new token.",
    )
    source = fields.Selection(
        [("manual", "Created by an administrator"),
         ("registered", "Registered by the application")],
        default="manual", readonly=True, copy=False,
    )
    last_used_on = fields.Datetime(
        readonly=True, copy=False,
        help="When this client last got a token. Empty: it never did.",
    )

    # Declared as a Constraint, not through _sql_constraints: since 19.0 the ORM
    # ignores that attribute.
    _client_id_uniq = models.Constraint(
        "unique (client_id)",
        "Another client already has that client ID.",
    )

    @api.constrains("redirect_uris")
    def _check_redirect_uris(self):
        for client in self:
            check_redirect_uris(split_uris(client.redirect_uris))

    # ---------------------------------------------------------------- settings
    @api.model
    def _dcr_enabled(self):
        return self.env["ir.config_parameter"].sudo().get_bool(PARAM_DCR)

    @api.model
    def _cimd_allowed_urls(self):
        return split_uris(self.env["ir.config_parameter"].sudo().get_str(PARAM_CIMD))

    # ----------------------------------------------------------------- resolve
    @api.model
    def _resolve(self, client_id):
        """What is known of a client, or None.

        :return: ``{"id", "client_id", "name", "redirect_uris": [...]}``; ``id``
            is the record, empty for a client known only by its metadata
            address. An archived client is unknown, so archiving it refuses it
            everywhere at once.
        """
        if not client_id:
            return None
        if client_id.startswith("https://"):
            return self._resolve_metadata_document(client_id)
        client = self.sudo().search([("client_id", "=", client_id)], limit=1)
        if not client:
            return None
        return {
            "id": client.id,
            "client_id": client.client_id,
            "name": client.name,
            "redirect_uris": split_uris(client.redirect_uris),
        }

    @api.model
    def _fetch_metadata(self, url):
        """The JSON document at ``url``. The one place that touches the network.

        No redirect is followed — a listed address that bounces somewhere else
        is not the address that was listed — and the answer is read only up to a
        fixed size, so a hostile or broken host cannot make this wait for, or
        hold, more than it should.
        """
        assert_public_host(urlsplit(url).hostname)
        response = requests.get(
            url, timeout=CIMD_TIMEOUT, allow_redirects=False, stream=True,
            headers={"Accept": "application/json"})
        try:
            if response.status_code != 200:
                raise ValidationError(_("The metadata document answered %s.",
                                        response.status_code))
            content = response.raw.read(CIMD_MAX_BYTES + 1, decode_content=True)
        finally:
            response.close()
        if len(content) > CIMD_MAX_BYTES:
            raise ValidationError(_("The metadata document is too large."))
        return json.loads(content)

    @api.model
    def _resolve_metadata_document(self, url):
        """A client named by the address of its own metadata document (CIMD)."""
        if url not in self._cimd_allowed_urls():
            _logger.info("plm_mcp: metadata address %s is not on the list", url)
            return None
        try:
            document = self._fetch_metadata(url)
            if not isinstance(document, dict) or document.get("client_id") != url:
                raise ValidationError(_("The document does not describe %s.", url))
            if document.get("token_endpoint_auth_method", "none") != "none":
                raise ValidationError(_("Only public clients are supported."))
            check_redirect_uris(document.get("redirect_uris"))
        except (ValidationError, requests.RequestException, ValueError) as error:
            _logger.info("plm_mcp: metadata document %s refused: %s", url, error)
            return None
        return {
            "id": None,
            "client_id": url,
            "name": clean_name(document.get("client_name"))
            or urlsplit(url).hostname,
            "redirect_uris": document["redirect_uris"],
        }

    # ---------------------------------------------------------- self-registration
    @api.model
    def _registration_open(self):
        """Whether one more application may register.

        Anyone can ask, so the number of registered applications that never got
        a token is capped: past it, registering waits for the clean-up.
        """
        unused = self.sudo().search_count([
            ("source", "=", "registered"), ("last_used_on", "=", False)])
        return unused < MAX_UNUSED_REGISTERED

    @api.model
    def _register(self, name, redirect_uris):
        """Create the client an application asked for (DCR).

        The addresses are checked before anything is written: a rejected
        registration returns an answer instead of raising, so the request
        commits, and a record written first would be committed with it.
        """
        check_redirect_uris(redirect_uris)
        return self.sudo().create({
            "name": clean_name(name) or _("Unnamed application"),
            "redirect_uris": "\n".join(redirect_uris),
            "source": "registered",
        })

    @api.model
    def _mark_used(self, client):
        """Note that a client, as ``_resolve`` returned it, got a token."""
        if client.get("id"):
            self.sudo().browse(client["id"]).last_used_on = fields.Datetime.now()

    @api.autovacuum
    def _gc_unused_registered_clients(self):
        limit = fields.Datetime.now() - timedelta(days=UNUSED_RETENTION_DAYS)
        self.sudo().with_context(active_test=False).search([
            ("source", "=", "registered"),
            ("last_used_on", "=", False),
            ("create_date", "<", limit),
        ]).unlink()
