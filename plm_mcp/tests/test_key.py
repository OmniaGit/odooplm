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
"""The credential, and the promise attached to it.

Two properties are worth a test each, because both fail silently. The clear
token must never be recoverable from the database — a leak there is a leak of
every key at once. And a call must run as the key's user, because that is the
whole permission model: there is no second set of rules for agents, and if the
environment were not switched the record rules would simply not apply.

    odoo --test-tags=odoo_plm_mcp -i plm_mcp -d <database>
"""
import hashlib
from datetime import date, timedelta

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-standard", "odoo_plm_mcp")
class TestKey(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Key = cls.env["plm.mcp.key"]
        cls.user = cls.env["res.users"].create({
            "name": "MCP test user",
            "login": "mcp_test_user",
            # A plain internal user cannot read mrp.bom, and the tools would refuse
            # for that reason alone. The rights given here are the ones a
            # person asking these questions would actually have.
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("mrp.group_mrp_user").id,
            ])],
        })

    def issue(self, **values):
        """A key, and the token it hands back exactly once."""
        key = self.Key.create(dict({
            "name": "Test key",
            "user_id": self.user.id,
        }, **values))
        return key, key.key_clear

    # ----------------------------------------------------------------- issue
    def test_a_new_key_hands_back_a_token(self):
        key, token = self.issue()
        self.assertTrue(token)
        self.assertTrue(key.key_digest)
        self.assertNotEqual(token, key.key_digest)

    def test_the_token_is_never_stored(self):
        """The clear value must not survive the transaction that created it.

        Read back from the database rather than from the record in memory: the
        field is non-stored, and only a fresh read proves it.
        """
        key, token = self.issue()
        self.env.flush_all()
        self.env.invalidate_all()
        reloaded = self.Key.browse(key.id)
        self.assertFalse(reloaded.key_clear)
        self.assertNotIn(token, str(reloaded.read()))

    def test_the_digest_is_the_sha256_of_the_token(self):
        key, token = self.issue()
        self.assertEqual(
            key.key_digest,
            hashlib.sha256(token.encode("utf-8")).hexdigest(),
        )

    def test_the_preview_shows_only_the_tail(self):
        """Enough to tell two keys apart, not enough to use one."""
        key, token = self.issue()
        self.assertIn(token[-6:], key.key_preview)
        self.assertNotIn(token[:10], key.key_preview)

    def test_regenerating_invalidates_the_previous_token(self):
        key, first = self.issue()
        key.action_regenerate()
        second = key.key_clear
        self.assertNotEqual(first, second)
        self.assertFalse(self.Key._authenticate(first))
        self.assertEqual(self.Key._authenticate(second), key)

    # ------------------------------------------------------------ authenticate
    def test_the_right_token_finds_its_key(self):
        key, token = self.issue()
        self.assertEqual(self.Key._authenticate(token), key)

    def test_a_wrong_or_empty_token_finds_nothing(self):
        self.issue()
        self.assertFalse(self.Key._authenticate("not-a-real-token"))
        self.assertFalse(self.Key._authenticate(""))
        self.assertFalse(self.Key._authenticate(None))

    def test_an_expired_key_is_refused(self):
        """Expiry is enforced at lookup, not left to whoever remembers."""
        key, token = self.issue()
        key.expires_on = date.today() - timedelta(days=1)
        self.assertFalse(self.Key._authenticate(token))

    def test_a_key_expiring_today_still_works(self):
        """The boundary belongs to the holder: a key is valid through its date."""
        key, token = self.issue()
        key.expires_on = date.today()
        self.assertEqual(self.Key._authenticate(token), key)

    def test_a_key_of_an_archived_user_is_refused(self):
        """Revoking the person must revoke their agent, without a second step."""
        key, token = self.issue()
        self.user.active = False
        self.assertFalse(self.Key._authenticate(token))

    def test_an_archived_key_is_refused(self):
        key, token = self.issue()
        key.active = False
        self.assertFalse(self.Key._authenticate(token))

    # ------------------------------------------------------------- execution
    def test_calls_run_as_the_keys_user(self):
        """The environment is switched — this is the whole permission model."""
        key, _token = self.issue()
        self.assertEqual(key.user_env().user, self.user)
        self.assertNotEqual(key.user_env().user, self.env.user)

    def test_a_tool_called_through_a_key_runs_as_that_user(self):
        key, _token = self.issue()
        tools = key.user_env()["plm.mcp.tool"]
        self.assertEqual(tools.env.user, self.user)
        result = tools._call_tool("plm_overview", {})
        self.assertFalse(result["isError"])

    def test_a_user_without_rights_is_refused_gracefully(self):
        """The security promise, seen from the other side.

        A key whose user cannot read the data does not get a broken server: the
        refusal comes back as an error result the model can read and explain.
        This is what makes record rules a usable permission model for an agent —
        found by a fixture that gave its user no manufacturing rights, which is
        exactly what happens when a key is issued to the wrong person.
        """
        stranger = self.env["res.users"].create({
            "name": "No rights at all",
            "login": "mcp_no_rights",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        key, _token = self.issue(user_id=stranger.id)
        result = key.user_env()["plm.mcp.tool"]._call_tool("plm_overview", {})
        self.assertTrue(result["isError"])
        self.assertIn("Bill of Material", result["content"][0]["text"])

    def test_usage_is_recorded(self):
        key, _token = self.issue()
        self.assertEqual(key.call_count, 0)
        key._register_call()
        self.assertEqual(key.call_count, 1)
        self.assertTrue(key.last_used_on)

    # ------------------------------------------------------------- integrity
    def test_the_unique_constraint_reached_the_database(self):
        """Asked of PostgreSQL, not of the Python declaration.

        The declaration is the part that broke: through the pre-19.0
        _sql_constraints attribute the ORM logs a warning and creates nothing,
        so the model looks constrained and the table is not. Only the catalogue
        can tell the two apart.
        """
        self.env.cr.execute("""
            SELECT pg_get_constraintdef(oid)
              FROM pg_constraint
             WHERE conrelid = 'plm_mcp_key'::regclass
               AND contype = 'u'
        """)
        definitions = [row[0] for row in self.env.cr.fetchall()]
        self.assertTrue(
            any("key_digest" in definition for definition in definitions),
            "no unique constraint on plm_mcp_key.key_digest: %s" % definitions,
        )
