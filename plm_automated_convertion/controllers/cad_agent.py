# -*- coding: utf-8 -*-
"""
Endpoints of the download and upload agents of the CAD workstation.

They work two operations of the conversion stack:
- CAD_VERSION: the files are updated to a new CAD version and uploaded back
- CONVERT (conversions of a CAD agent server): the starting files are only
  read; the converted files (DWG, STEP, flat pattern DXF, ...) update or
  create their converted documents

The agent logs in as a user of the group Plm Convert Admin (the session of
/web/session/authenticate) and calls:

- POST /plm_cad_agent/next_batch: takes the next rows and returns the files
  to download (hostname, hostpws, limit, operation_type CAD_VERSION|CONVERT,
  cad_name: the CAD of the workstation, only the rows of its conversions)
- GET  /plm_cad_agent/download: the file of a document (document_id)
- POST /plm_cad_agent/upload: a file produced for a row (stack_id, file,
  cad_version for an update, variant = model state for a conversion)
- POST /plm_cad_agent/report: closes a row (stack_id, state
  error|skipped, or done for a conversion, message)
"""
import logging

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

CONVERT_ADMIN_GROUP = "plm_automated_convertion.group_plm_convert_admin"


class CadAgentController(http.Controller):
    def _check_access(self):
        if not request.env.user.has_group(CONVERT_ADMIN_GROUP):
            raise AccessError("Only a Plm Convert Admin can run the CAD agents.")

    def _json_error(self, ex, status=400):
        return request.make_json_response({"error": str(ex)}, status=status)

    def _stack_row(self, stack_id):
        row = request.env["plm.convert.stack"].sudo().browse(int(stack_id)).exists()
        if not row:
            raise UserError("Row %s not found." % stack_id)
        return row

    @http.route("/plm_cad_agent/next_batch", type="http", auth="user", methods=["POST"], csrf=False)
    def next_batch(self, hostname="", hostpws="", limit=10, operation_type="CAD_VERSION", cad_name="", **kw):
        try:
            self._check_access()
            data = (
                request.env["plm.convert.stack"]
                .sudo()
                .cad_agent_next_batch(hostname, hostpws, int(limit), operation_type, cad_name)
            )
        except (AccessError, UserError) as ex:
            return self._json_error(ex, 403 if isinstance(ex, AccessError) else 400)
        return request.make_json_response(data)

    @http.route("/plm_cad_agent/download", type="http", auth="user", methods=["GET"])
    def download(self, document_id, **kw):
        try:
            self._check_access()
        except AccessError as ex:
            return self._json_error(ex, 403)
        document = (
            request.env["ir.attachment"]
            .sudo()
            .search([("id", "=", int(document_id)), ("is_plm", "=", True)], limit=1)
        )
        if not document:
            return self._json_error("Document %s not found." % document_id, 404)
        return request.env["ir.binary"].sudo()._get_stream_from(document, field_name="raw").get_response(
            as_attachment=True
        )

    @http.route("/plm_cad_agent/upload", type="http", auth="user", methods=["POST"], csrf=False)
    def upload(self, stack_id, file=None, cad_version="", variant="", **kw):
        try:
            self._check_access()
            if file is None:
                raise UserError("No file uploaded.")
            state, message = self._stack_row(stack_id).cad_agent_upload(file.read(), cad_version, variant)
        except (AccessError, UserError) as ex:
            return self._json_error(ex, 403 if isinstance(ex, AccessError) else 400)
        return request.make_json_response({"state": state, "message": message})

    @http.route("/plm_cad_agent/report", type="http", auth="user", methods=["POST"], csrf=False)
    def report(self, stack_id, state="error", message="", **kw):
        try:
            self._check_access()
            self._stack_row(stack_id).cad_agent_report(state, message)
        except (AccessError, UserError) as ex:
            return self._json_error(ex, 403 if isinstance(ex, AccessError) else 400)
        return request.make_json_response({"state": state})
