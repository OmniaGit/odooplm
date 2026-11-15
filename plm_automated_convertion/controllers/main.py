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
"""What a CAD workstation (CoreBomWeb) calls. It logs in as a user of the
group Plm Convert Admin (/web/session/authenticate) and calls:

- POST /plm_cad_agent/register: presents itself (JSON body, see
  plm.convert.servers.register_workstation); answers its server id, name and
  whether it is enabled
"""
import json

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

CONVERT_ADMIN_GROUP = "plm_automated_convertion.group_plm_convert_admin"


class CadWorkstationController(http.Controller):
    def _json_error(self, message, status=400):
        return request.make_json_response({"error": str(message)}, status=status)

    @http.route("/plm_cad_agent/register", type="http", auth="user", methods=["POST"], csrf=False)
    def register(self, **kw):
        if not request.env.user.has_group(CONVERT_ADMIN_GROUP):
            return self._json_error("Only a Plm Convert Admin can register a CAD workstation.", 403)
        try:
            data = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except ValueError:
            return self._json_error("The body is not JSON.")
        try:
            answer = request.env["plm.convert.servers"].sudo().register_workstation(data)
        except (AccessError, UserError) as ex:
            return self._json_error(ex)
        return request.make_json_response(answer)
