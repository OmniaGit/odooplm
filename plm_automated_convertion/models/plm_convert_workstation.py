##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2026 OmniaSolutions (<https://www.omniasolutions.website>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""CAD workstations (CoreBomWeb): they register themselves, by the GUID of
their machine, and present what they can do (DESIGN.md, CAD workstations)."""
import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# a workstation is alive when it called Odoo in the last minutes
ALIVE_MINUTES = 10
EXPORT_MODES = [
    ("file", "One File"),
    ("model_state", "One File Per Model State"),
    ("flat_pattern", "Sheet Metal Flat Pattern"),
]


class PlmConvertServers(models.Model):
    _inherit = "plm.convert.servers"

    cad_agent = fields.Boolean(
        "CAD Agent",
        help="The conversions of this server are made by the agents of a CAD workstation, "
        "which take them from the conversion stack: Odoo never converts them itself.",
    )
    workstation_guid = fields.Char(
        "Workstation GUID",
        index=True,
        copy=False,
        readonly=True,
        help="The machine UUID of the CAD workstation, as its license computes it: "
        "the workstation is found by it when it registers again.",
    )
    hostname = fields.Char("Computer", readonly=True)
    agent_version = fields.Char("CoreBomWeb Version", readonly=True)
    last_contact = fields.Datetime("Last Contact", readonly=True)
    alive = fields.Boolean("Alive", compute="_compute_alive")
    work_hours = fields.Text(
        "Work Hours",
        readonly=True,
        help="When the workstation starts jobs by itself, crontab expressions; empty: always.",
    )
    features = fields.Char("Functions", readonly=True, help="What the workstation can do besides converting.")
    workstation_cad_ids = fields.One2many("plm.convert.servers.cad", "server_id", string="CADs", readonly=True)
    group_ids = fields.Many2many(
        "res.groups",
        "plm_convert_servers_res_groups_rel",
        "server_id",
        "group_id",
        string="User Groups",
        help="Empty: the workstation works the jobs of every user without a workstation of his own groups. "
        "Set: it works only the jobs of the users of these groups, and those users only use the "
        "workstations of their groups.",
    )

    _sql_constraints = [
        ("workstation_guid_unique", "unique(workstation_guid)", "A workstation with this GUID exists already."),
    ]

    @api.depends("last_contact")
    def _compute_alive(self):
        limit = fields.Datetime.now() - datetime.timedelta(minutes=ALIVE_MINUTES)
        for server in self:
            server.alive = bool(server.last_contact and server.last_contact >= limit)

    @api.model
    def register_workstation(self, data):
        """A CAD workstation presents itself: found by its GUID, else created
        (new ones start enabled, as every workstation works for every user by
        default). data: {"guid", "hostname", "version", "work_hours": [...],
        "features": [...], "cads": [{"name", "version", "prog_id"}],
        "conversions": [{"cad", "start_format", "end_format", "export_mode"}]}.
        :return {"server_id", "name", "enabled"}
        """
        if not isinstance(data, dict) or not (data.get("guid") or "").strip():
            raise UserError(_("A workstation registers with the GUID of its machine."))
        guid = data["guid"].strip()
        hostname = (data.get("hostname") or "").strip()
        values = {
            "hostname": hostname,
            "agent_version": data.get("version") or "",
            "last_contact": fields.Datetime.now(),
            "work_hours": "\n".join(data.get("work_hours") or []),
            "features": ", ".join(data.get("features") or []),
            # a workstation takes its jobs from the queue: Odoo never converts them
            "cad_agent": True,
        }
        server = self.with_context(active_test=False).search([("workstation_guid", "=", guid)], limit=1)
        if server:
            server.write(values)
        else:
            server = self.create(
                dict(values, workstation_guid=guid, name=hostname or guid, available=True, is_internal=False)
            )
        server._present_cads(data.get("cads") or [])
        server._present_conversions(data.get("conversions") or [])
        return {"server_id": server.id, "name": server.name, "enabled": server.available}

    def _feature_list(self):
        self.ensure_one()
        return [name.strip() for name in (self.features or "").split(",") if name.strip()]

    def _users_tied_to_workstations(self):
        """The users of the groups tied to a workstation: their jobs are worked
        only by the workstations of their groups."""
        return self.with_context(active_test=False).search([("group_ids", "!=", False)]).mapped("group_ids.users")

    def _queue_requester_domain(self):
        """The jobs this workstation may take, by who asked for them: with
        groups, only the jobs of the users of its groups; without groups
        (shared), the jobs of the users not tied to any workstation."""
        self.ensure_one()
        if self.group_ids:
            return [("requester_id", "in", self.group_ids.users.ids)]
        tied = self._users_tied_to_workstations()
        if not tied:
            return []
        return ["|", ("requester_id", "=", False), ("requester_id", "not in", tied.ids)]

    def _queue_conversion_domain(self, operation_type):
        """The jobs this workstation can do: a CAD version update of one of
        its CADs, when it presented the function CAD_VERSION; a conversion it
        presented (CAD, start and end format, export mode), whatever server
        the conversion rule of the job belongs to."""
        self.ensure_one()
        stack = self.env["plm.convert.stack"]
        if operation_type == "CAD_VERSION":
            if "CAD_VERSION" not in self._feature_list():
                return None
            domains = [stack._cad_agent_cad_domain(cad.cad_name) for cad in self.workstation_cad_ids]
            domains = [domain for domain in domains if domain]
            if not domains:
                return None
            return ["|"] * (len(domains) - 1) + [term for domain in domains for term in domain]
        conversions = self.available_format.filtered(lambda f: f.available and f.cad_export_mode)
        if not conversions:
            return None
        domain = ["|"] * (len(conversions) - 1)
        for conversion in conversions:
            domain += [
                "&", "&", "&",
                ("convrsion_rule.cad_name", "=ilike", conversion.cad_name),
                ("convrsion_rule.start_format", "=ilike", conversion.start_format),
                ("convrsion_rule.end_format", "=ilike", conversion.end_format),
                ("convrsion_rule.cad_export_mode", "=", conversion.cad_export_mode),
            ]
        return domain

    def _present_cads(self, cads):
        self.ensure_one()
        self.workstation_cad_ids.unlink()
        lines = []
        for cad in cads:
            if not isinstance(cad, dict) or not cad.get("name"):
                continue
            lines.append(
                {
                    "server_id": self.id,
                    "cad_name": cad["name"],
                    "cad_version": cad.get("version") or "",
                    "prog_id": cad.get("prog_id") or "",
                }
            )
        self.env["plm.convert.servers.cad"].create(lines)

    def _present_conversions(self, conversions):
        """The formats the workstation presented: created when new, made
        available again when presented, unavailable when no more presented.
        Formats made by hand are not touched."""
        self.ensure_one()
        modes = dict(EXPORT_MODES)
        formats = self.env["plm.convert.format"].with_context(active_test=False)
        presented = formats.browse()
        for conversion in conversions:
            if not isinstance(conversion, dict):
                continue
            start, end = _extension(conversion.get("start_format")), _extension(conversion.get("end_format"))
            cad_name = (conversion.get("cad") or "").strip()
            mode = conversion.get("export_mode") or "file"
            if not start or not end or not cad_name or mode not in modes:
                continue
            found = formats.search(
                [
                    ("server_id", "=", self.id),
                    ("start_format", "=ilike", start),
                    ("end_format", "=ilike", end),
                    ("cad_name", "=ilike", cad_name),
                    ("cad_export_mode", "=", mode),
                ],
                limit=1,
            )
            if not found:
                found = formats.create(
                    {
                        "server_id": self.id,
                        "start_format": start,
                        "end_format": end,
                        "cad_name": cad_name,
                        "cad_export_mode": mode,
                    }
                )
            found.write({"available": True, "presented": True})
            presented |= found
        (formats.search([("server_id", "=", self.id), ("presented", "=", True)]) - presented).write(
            {"available": False}
        )


def _extension(value):
    value = (value or "").strip().lower()
    if value and not value.startswith("."):
        value = "." + value
    return value


class PlmConvertServersCad(models.Model):
    _name = "plm.convert.servers.cad"
    _description = "CAD of a CAD workstation"
    _order = "cad_name"

    server_id = fields.Many2one("plm.convert.servers", string="Workstation", required=True, ondelete="cascade")
    cad_name = fields.Char("CAD", required=True)
    cad_version = fields.Char("Version")
    prog_id = fields.Char("COM ProgID")


class PlmConvertFormat(models.Model):
    _inherit = "plm.convert.format"

    cad_export_mode = fields.Selection(
        EXPORT_MODES,
        string="CAD Export Mode",
        help="What a CAD workstation exports from the starting file; it also gives the code "
        "of the converted document, the same the CAD client gives it at check-in.",
    )
    cad_version_update = fields.Boolean(
        "CAD Version Update",
        help="The conversion updates the files of the start format to the target version of its CAD "
        "(PLM dictionaries, CAD Versions).",
    )
    presented = fields.Boolean(
        "Presented by the Workstation",
        readonly=True,
        help="Made by the workstation when it registered: it becomes unavailable when the workstation "
        "no longer presents it.",
    )

    @api.constrains("cad_export_mode", "cad_version_update")
    def _check_export_or_version_update(self):
        """A rule either exports (a conversion of the workstation) or updates
        the file to the target CAD version, never both: a conversion marked
        as CAD version update leaves the conversion wizard and makes the
        Massive Update find two version updates for one format."""
        for rule in self:
            if rule.cad_export_mode and rule.cad_version_update:
                raise ValidationError(
                    _(
                        "%(rule)s: a conversion with a CAD export mode cannot also be a CAD version update; "
                        "a CAD version update starts and ends with the same format and has no export mode.",
                        rule=rule.display_name,
                    )
                )
