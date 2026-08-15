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
"""Where OdooBot is taught to recognise the PLM commands.

Deliberately thin. _apply_logic already decides when the bot should speak at
all — in a chat with it, or when it is mentioned — and posts whatever comes
back; the only thing added here is one branch. Everything the bot does not
recognise as ours goes straight to super(), so the onboarding conversation and
every other answer are untouched.

The command runs in the environment of whoever typed it, which is what makes
this safe: a part that user cannot see is a part the answer will not mention.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailBot(models.AbstractModel):
    _inherit = "mail.bot"

    def _get_answer(self, channel, body, values, command=False):
        text = self.env["plm.mcp.bot"]._command_text(body)
        if text:
            _logger.info("plm_mcp_bot: %s asked %r",
                         self.env.user.login, text)
            return self.env["plm.mcp.bot"]._answer(text)
        return super()._get_answer(channel, body, values, command)
