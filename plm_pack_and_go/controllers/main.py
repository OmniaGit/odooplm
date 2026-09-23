##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    $Id$
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
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class PackAndGoDownload(http.Controller):

    @http.route(
        "/plm_pack_and_go/download/<int:wizard_id>",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def download_zip(self, wizard_id, **kw):
        """Serve the archive built by the Pack and Go wizard.

        The archive used to be offered through the binary field widget, which
        downloads with a POST and therefore carries a CSRF token: a page opened
        before the session was renewed then fails with "Session expired
        (invalid CSRF token)" instead of downloading. A GET is not CSRF
        protected, so the wizard returns an ir.actions.act_url to this route.

        The wizard is a transient model, on which no record rule applies, so
        the archive is given back only to the user who built it.
        """
        wizard = request.env["pack.and_go"].browse(wizard_id).exists()
        if not wizard:
            raise NotFound()
        wizard.check_access("read")
        if wizard.create_uid != request.env.user or not wizard.datas:
            raise NotFound()
        return (
            request.env["ir.binary"]
            ._get_stream_from(
                wizard, field_name="datas", filename=wizard.datas_fname
            )
            .get_response(as_attachment=True)
        )


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
