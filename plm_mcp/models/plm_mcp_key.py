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
"""The credential an MCP client presents, and the user its calls run as.

A key is not an identity of its own: it points at a res.users, and every tool
call is executed with that user's environment. Whatever the PLM record rules
hide from that user stays hidden from the agent — there is no separate
permission model to keep in sync, and no way for a key to reach further than
the person it was issued for.

The token itself is never stored. What is kept is its SHA-256, which is what
the endpoint looks the key up by; the clear value is shown once, at creation,
and cannot be recovered afterwards. A token is high-entropy random, so a plain
digest is the right primitive here — this is a lookup key, not a password, and
stretching it would only slow down every request.
"""
import hashlib
import logging
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TOKEN_BYTES = 32


def _digest(token):
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


class PlmMcpKey(models.Model):
    _name = "plm.mcp.key"
    _description = "PLM MCP API Key"
    _order = "name"

    name = fields.Char(
        required=True,
        help="What this key is for — the client or the person using it.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Runs as",
        required=True,
        default=lambda self: self.env.user,
        help="Tool calls execute as this user, with their PLM access rights.",
    )
    active = fields.Boolean(default=True)
    expires_on = fields.Date(
        help="After this date the key stops working. Empty means no expiry.",
    )

    key_digest = fields.Char(
        string="Key Digest", readonly=True, copy=False, index=True,
    )
    key_preview = fields.Char(
        string="Key", readonly=True, copy=False,
        help="The last characters of the token, to tell keys apart.",
    )
    # Not stored: the clear token exists only in the response of the call that
    # created it. Reloading the form after that shows nothing.
    key_clear = fields.Char(string="Token", readonly=True, store=False)

    last_used_on = fields.Datetime(readonly=True, copy=False)
    call_count = fields.Integer(readonly=True, copy=False, default=0)

    # Declared as a Constraint, not through _sql_constraints: since 19.0 the ORM
    # ignores that attribute — it logs a warning and creates nothing, which
    # would leave two keys free to share a digest.
    _key_digest_uniq = models.Constraint(
        "unique (key_digest)",
        "That key already exists.",
    )

    # ------------------------------------------------------------------ issue
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._issue_token()
        return records

    def _issue_token(self):
        """Mint a token, keep its digest, hand the clear value back once."""
        self.ensure_one()
        token = secrets.token_urlsafe(TOKEN_BYTES)
        self.write({
            "key_digest": _digest(token),
            "key_preview": "…%s" % token[-6:],
        })
        # write() would drop a non-stored field, so it is set on the record
        # itself — it lives for this transaction and this response only.
        self.key_clear = token
        return token

    def action_regenerate(self):
        """Replace the token. The previous one stops working immediately."""
        for record in self:
            record._issue_token()
            _logger.info("plm_mcp: token regenerated for key %s", record.name)
        return True

    # --------------------------------------------------------------- validate
    @api.model
    def _authenticate(self, token):
        """The key this token belongs to, or an empty recordset.

        Looked up by digest rather than compared in Python: the database index
        does the work, and no clear token is ever loaded to be compared against.
        Expiry is checked here so a stale key cannot be used even if the record
        is still active.
        """
        if not token:
            return self.browse()
        key = self.sudo().search([("key_digest", "=", _digest(token))], limit=1)
        if not key:
            return self.browse()
        if key.expires_on and key.expires_on < fields.Date.context_today(key):
            _logger.info("plm_mcp: key %s refused, expired on %s",
                         key.name, key.expires_on)
            return self.browse()
        if not key.user_id.active:
            _logger.info("plm_mcp: key %s refused, user %s is archived",
                         key.name, key.user_id.login)
            return self.browse()
        return key

    def _register_call(self):
        """Record that the key was used. Cheap, and the only usage trail there is."""
        self.ensure_one()
        self.sudo().write({
            "last_used_on": fields.Datetime.now(),
            "call_count": self.call_count + 1,
        })

    def user_env(self):
        """An environment scoped to the key's user — how every tool must run."""
        self.ensure_one()
        if not self.user_id:
            raise UserError(_("The key %s has no user to run as.") % self.name)
        return self.env(user=self.user_id.id)
