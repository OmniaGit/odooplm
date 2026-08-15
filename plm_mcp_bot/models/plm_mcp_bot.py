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
"""The commands, and how their answers are written for a chat window.

The tools are the ones the MCP server exposes — same registry, same method,
same record rules. What this adds is a way to reach them by typing, for people
who have Odoo open and no MCP client at hand.

Two things shape the code below.

The message arrives lowercased and still wrapped in HTML: ``_apply_logic``
lowercases the body before handing it over and never strips the markup, so what
looks like ``/plm bom base-100`` is really ``<p>/plm bom base-100</p>``.
Everything is normalised once, up front. Engineering codes surviving in
lowercase costs nothing — every lookup in the suite matches with ``=ilike``.

And an answer is read in a chat window, not parsed: the payloads the tools
return are shaped for a model that reads JSON, so each command has a formatter
that turns its answer into a few lines a person can take in at a glance. That
is most of this file, and it is the part that decides whether the thing gets
used.
"""
import logging

from markupsafe import Markup, escape

from odoo import _, api, models
from odoo.tools.mail import html2plaintext

_logger = logging.getLogger(__name__)

PREFIX = "/plm"
MAX_ROWS = 25


class PlmMcpBot(models.AbstractModel):
    _name = "plm.mcp.bot"
    _description = "PLM Commands for OdooBot"

    # command -> (tool, formatter, argument, one-line help)
    def _commands(self):
        return {
            "bom": ("plm_bom", "_format_bom", "codice",
                    _("the bill of material of a part")),
            "parte": ("plm_part_detail", "_format_part", "codice",
                      _("the title block and documents of a part")),
            "dove": ("plm_where_used", "_format_where_used", "codice",
                     _("the assemblies a part is used in, by revision")),
            "impatto": ("plm_change_impact", "_format_impact", "codice",
                        _("what modifying a part would touch")),
            "mancanti": ("plm_documents", "_format_missing", "codice",
                         _("the components with no drawing")),
            "aperti": ("plm_in_progress", "_format_in_progress", None,
                       _("what is under modification, and by whom")),
        }

    # ------------------------------------------------------------- entry point
    @api.model
    def _command_text(self, body):
        """The typed command, or False when the message is not for us.

        Returns the plain text so that the caller does not have to know the
        message arrived as HTML.
        """
        text = html2plaintext(body or "").strip()
        if not text.lower().startswith(PREFIX):
            return False
        return text

    @api.model
    def _answer(self, text):
        """Run one command and write its answer."""
        parts = text.split()[1:]  # drop the prefix itself
        if not parts:
            return self._help()

        name = parts[0].lower()
        commands = self._commands()
        if name not in commands:
            return Markup("%s<br/>%s") % (
                _("I do not know the command %s.") % name, self._help())

        tool, formatter, argument, _description = commands[name]
        arguments, unnamed = self._parse_arguments(parts[1:])
        if argument:
            if not unnamed:
                return escape(
                    _("%(command)s needs a %(argument)s, "
                      "for example: %(prefix)s %(command)s BASE-100")
                    % {"command": name, "argument": argument, "prefix": PREFIX})
            arguments["code"] = unnamed[0]
        if name == "mancanti":
            arguments.setdefault("missing", "drawing")

        try:
            payload = self.env["plm.mcp.tool"]._call_tool(tool, arguments)
        except Exception as error:  # noqa: BLE001 - reported, never raised at a chat
            _logger.info("plm_mcp_bot: %s failed: %s", name, error)
            return escape(_("That command could not run: %s") % error)

        if payload.get("isError"):
            return escape(payload["content"][0]["text"])
        return getattr(self, formatter)(payload["structuredContent"])

    @api.model
    def _parse_arguments(self, tokens):
        """``depth=3`` becomes an argument; anything else is positional."""
        arguments, unnamed = {}, []
        for token in tokens:
            if "=" in token:
                key, _sep, value = token.partition("=")
                arguments[key.strip()] = self._typed(value.strip())
            else:
                unnamed.append(token)
        return arguments, unnamed

    @api.model
    def _typed(self, value):
        """Numbers and booleans typed in a chat arrive as text."""
        if value.isdigit():
            return int(value)
        if value in ("true", "false"):
            return value == "true"
        return value

    # -------------------------------------------------------------------- help
    @api.model
    def _help(self):
        """Built from the command table, so it cannot fall out of step."""
        lines = [escape(_("Commands:"))]
        for name, (_tool, _formatter, argument, description) in \
                sorted(self._commands().items()):
            usage = "%s %s %s" % (PREFIX, name, (argument or "").upper())
            lines.append(Markup("<b>%s</b> — %s") % (usage.strip(), description))
        return Markup("<br/>").join(lines)

    # -------------------------------------------------------------- formatters
    @api.model
    def _render_table(self, headers, rows, note=None):
        """A small HTML table — chat windows are narrow, so keep it lean."""
        if not rows:
            return escape(note or _("Nothing to show."))
        head = Markup("").join(Markup("<th>%s</th>") % escape(h) for h in headers)
        body = Markup("").join(
            Markup("<tr>%s</tr>") % Markup("").join(
                Markup("<td>%s</td>") % escape("" if cell is None else cell)
                for cell in row)
            for row in rows[:MAX_ROWS])
        table = Markup(
            "<table class='table table-sm'><tr>%s</tr>%s</table>") % (head, body)
        if len(rows) > MAX_ROWS:
            table += escape(
                _("… and %s more.") % (len(rows) - MAX_ROWS))
        if note:
            table += Markup("<br/>%s") % escape(note)
        return table

    @api.model
    def _format_bom(self, payload):
        title = Markup("<b>%s</b> rev %s — %s<br/>") % (
            escape(payload["engineering_code"]),
            escape(payload["engineering_revision"]),
            escape(payload.get("name") or ""))
        if not payload.get("has_bom"):
            return title + escape(payload.get("note") or _("No bill of material."))
        rows = [(line["engineering_code"], line["quantity"],
                 line.get("name"), line.get("engineering_material") or "-")
                for line in payload["lines"]]
        return title + self._render_table(
            [_("Code"), _("Qty"), _("Name"), _("Material")], rows)

    @api.model
    def _format_part(self, payload):
        rows = [
            (_("Revision"), "%s%s" % (
                payload["engineering_revision"],
                _(" (latest)") if payload.get("is_latest") else "")),
            (_("State"), payload.get("engineering_state")),
            (_("Material"), payload.get("engineering_material") or "-"),
            (_("Category"), payload.get("category") or "-"),
            (_("Documents"), len(payload.get("documents") or [])),
        ]
        title = Markup("<b>%s</b> — %s<br/>") % (
            escape(payload["engineering_code"]), escape(payload.get("name") or ""))
        return title + self._render_table([_("Field"), _("Value")], rows)

    @api.model
    def _format_where_used(self, payload):
        rows = []
        for revision in payload.get("revisions", []):
            for row in revision.get("used_in", []):
                rows.append((revision["engineering_revision"],
                             row["engineering_code"],
                             row.get("quantity"),
                             row.get("engineering_state")))
        return Markup("<b>%s</b><br/>") % escape(payload["engineering_code"]) \
            + self._render_table(
                [_("Rev"), _("Used in"), _("Qty"), _("State")], rows,
                note=None if rows else _("Not used in any assembly."))

    @api.model
    def _format_impact(self, payload):
        part = payload["part"]
        lines = [Markup("<b>%s</b> rev %s — %s") % (
            escape(part["engineering_code"]),
            escape(part["engineering_revision"]),
            escape(part.get("name") or ""))]
        for revision in payload.get("impact", []):
            lines.append(escape(
                _("rev %(rev)s: %(count)s assemblies, %(released)s released")
                % {"rev": revision["engineering_revision"],
                   "count": revision["assemblies_count"],
                   "released": revision["assemblies_released"]}))
        raised = [name for name, value in payload.get("flags", {}).items() if value]
        lines.append(escape(
            _("Flags: %s") % (", ".join(raised) or _("none"))))
        return Markup("<br/>").join(lines)

    @api.model
    def _format_missing(self, payload):
        rows = [(row["engineering_code"], row.get("name"),
                 _("yes") if row.get("has_model") else _("no"))
                for row in payload.get("components", [])]
        return self._render_table(
            [_("Code"), _("Name"), _("Has model")], rows,
            note=None if rows else _("Every component has a drawing."))

    @api.model
    def _format_in_progress(self, payload):
        rows = [(row["engineering_code"], row["engineering_revision"],
                 row["engineering_state"], row.get("workflow_user") or "-")
                for row in (payload.get("parts") or [])
                + (payload.get("documents") or [])]
        return self._render_table(
            [_("Code"), _("Rev"), _("State"), _("Who")], rows,
            note=None if rows else _("Nothing is under modification."))
