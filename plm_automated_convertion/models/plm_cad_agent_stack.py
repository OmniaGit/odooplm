# -*- coding: utf-8 -*-
import logging
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .plm_cad_agent_attachment import UPGRADED_OPERATION

_logger = logging.getLogger(__name__)

CAD_VERSION_OPERATION = "CAD_VERSION"
# the conversion of plm_automated_convertion; its rows are worked by the
# agent when the server of their conversion is a CAD agent
CONVERT_OPERATION = "CONVERT"
CAD_AGENT_OPERATIONS = [CAD_VERSION_OPERATION, CONVERT_OPERATION]
DRAFT_STATE = "draft"
# rows waiting for an agent or held by one
OPEN_CAD_AGENT_STATES = ["to_do", "downloaded"]
# rows searched for the next batch at a time
NEXT_BATCH_CHUNK = 200
# relation of the files converted from a document
EXTRA_LINK_KIND = "ExtraTree"
# converted documents are always in revision 0, as the client saves them
CONVERTED_REVISION = 0
# the configuration name of a product of a CAD without configurations
NO_CONFIGURATION = "NO_CONFIGURATION"


class PlmConvertStack(models.Model):
    _inherit = "plm.convert.stack"

    operation_type = fields.Selection(
        selection_add=[(CAD_VERSION_OPERATION, "CAD Version Update")],
        ondelete={CAD_VERSION_OPERATION: "cascade"},
    )
    cad_agent = fields.Boolean(related="server_id.cad_agent", string="CAD Agent")
    cad_version_target = fields.Char("Target CAD Version", readonly=True)
    # the state of every job, worked by Odoo or by a CAD workstation
    cad_agent_state = fields.Selection(
        [
            ("to_do", "To Do"),
            ("downloaded", "In Progress"),
            ("done", "Done"),
            ("error", "Error"),
            ("skipped", "Skipped"),
        ],
        string="State",
        default="to_do",
        readonly=True,
        index=True,
        copy=False,
    )
    requester_id = fields.Many2one(
        "res.users",
        "Requested By",
        default=lambda self: self.env.user,
        readonly=True,
        index=True,
        ondelete="set null",
        help="Who asked for the job: the workstations tied to his groups work it.",
    )
    workstation_id = fields.Many2one(
        "plm.convert.servers",
        "Taken By",
        readonly=True,
        copy=False,
        index=True,
        ondelete="set null",
        help="The CAD workstation working the job, or that worked it.",
    )
    cad_download_date = fields.Datetime("Download Date", readonly=True, copy=False)
    cad_upload_date = fields.Datetime("Upload Date", readonly=True, copy=False)
    cad_hostname = fields.Char("Workstation", readonly=True, copy=False)
    cad_hostpws = fields.Char("Working Directory", readonly=True, copy=False)
    cad_download_engineering_state = fields.Char(
        "State At Download",
        readonly=True,
        copy=False,
        help="State of the document when the agent downloaded it: the upload is refused if it changed.",
    )
    cad_checkout_id = fields.Many2one(
        "plm.checkout",
        "Batch Check-Out",
        readonly=True,
        copy=False,
        ondelete="set null",
        help="Check-out the update holds on a draft document while the agent works on it.",
    )
    cad_export_document_ids = fields.Many2many(
        "ir.attachment",
        "plm_convert_stack_cad_export_rel",
        "stack_id",
        "document_id",
        string="Converted Documents",
        readonly=True,
        copy=False,
        help="Documents the agent created or updated from the conversion of the starting document.",
    )

    @api.constrains("operation_type", "convrsion_rule")
    def _check_cad_agent_rule(self):
        for row in self:
            if row.operation_type == CAD_VERSION_OPERATION and not row.convrsion_rule.cad_version_update:
                raise ValidationError(_("A CAD version update needs a conversion marked as CAD version update."))
            if (
                row.operation_type == CONVERT_OPERATION
                and row.convrsion_rule.server_id.cad_agent
                and not row.convrsion_rule.cad_export_mode
            ):
                raise ValidationError(_("A conversion of a CAD agent needs its CAD export mode."))

    def convert(self):
        # the rows of a CAD agent are converted by the agent, never by Odoo
        return super(PlmConvertStack, self.filtered(lambda row: not row.server_id.cad_agent)).convert()

    def _cad_agent_document(self):
        return self.start_document_id.sudo()

    # ------------------------------------------------------------------
    # Next batch
    # ------------------------------------------------------------------

    @api.model
    def cad_agent_next_batch(
        self, hostname, hostpws, limit=10, operation_type=CAD_VERSION_OPERATION, cad_name="", guid=""
    ):
        """Take the next rows of the operation and return the files the agent
        has to download.
        :hostname the workstation of the agent
        :hostpws the working directory of the agent
        :limit how many documents to take: rows for a CAD version update,
            starting documents for a conversion (all their conversions
            together)
        :operation_type CAD_VERSION or CONVERT
        :cad_name the CAD of the workstation (inventor, SolidWorks...): only the
            rows of its conversions; empty: the rows of every CAD. Not used
            with a GUID.
        :guid the GUID of a registered workstation: only the jobs it can do
            (its CADs and the conversions it presented) and may take (the
            groups of the requester, see plm.convert.servers
            _queue_requester_domain). Empty: an agent that did not register,
            the jobs of every user
        :return {"rows": [...], "files": [...]}, see _cad_agent_batch_data
        """
        if not hostname or not hostpws:
            raise UserError(_("The workstation and its working directory are required."))
        if operation_type not in CAD_AGENT_OPERATIONS:
            raise UserError(_("The operation %s is not worked by a CAD agent.", operation_type))
        domain = [
            ("operation_type", "=", operation_type),
            ("cad_agent_state", "=", "to_do"),
        ]
        if operation_type == CONVERT_OPERATION:
            domain.append(("convrsion_rule.server_id.cad_agent", "=", True))
        workstation = self.env["plm.convert.servers"]
        if guid:
            workstation = workstation.with_context(active_test=False).search(
                [("workstation_guid", "=", guid)], limit=1
            )
            if not workstation:
                raise UserError(_("The workstation %s is not registered: it presents itself first.", guid))
            if not workstation.available:
                return {"rows": [], "files": [], "message": _("The workstation is disabled on Odoo.")}
            conversion_domain = workstation._queue_conversion_domain(operation_type)
            if conversion_domain is None:
                return {"rows": [], "files": []}
            domain += conversion_domain + workstation._queue_requester_domain()
        else:
            domain += self._cad_agent_cad_domain(cad_name)
        self = self.with_context(cad_agent_workstation_id=workstation.id)
        to_do_ids = self.search(domain, order="sequence ASC, id ASC").ids
        picked = self.browse()
        seen_document_ids = set()
        taken = 0
        for start in range(0, len(to_do_ids), NEXT_BATCH_CHUNK):
            for row in self.browse(to_do_ids[start : start + NEXT_BATCH_CHUNK]):
                if taken >= limit:
                    break
                if operation_type == CAD_VERSION_OPERATION:
                    if row._cad_version_lock(hostname, hostpws):
                        picked |= row
                        taken += 1
                    continue
                if row.start_document_id.id in seen_document_ids:
                    continue
                seen_document_ids.add(row.start_document_id.id)
                rows = self.search(
                    domain + [("start_document_id", "=", row.start_document_id.id)],
                    order="sequence ASC, id ASC",
                )
                if rows._cad_export_lock(hostname, hostpws):
                    picked |= rows
                    taken += 1
            if taken >= limit:
                break
        return picked._cad_agent_batch_data()

    def _cad_export_model_states(self):
        """The model states to export for a conversion in mode model_state:
        the configurations of the products of the starting document (their
        Configuration Name); [] for the other modes, or when no product has
        one (the agent then exports the active model state)."""
        self.ensure_one()
        if self.convrsion_rule.cad_export_mode != "model_state":
            return []
        names = self._cad_agent_document().linkedcomponents.mapped("configuration_name")
        return sorted({name.strip() for name in names if name and name.strip() and name.strip() != NO_CONFIGURATION})

    @api.model
    def _cad_agent_cad_domain(self, cad_name):
        """The rows of the conversions of a CAD: the conversions write its name
        (Inventor), the workstation may send its name or its code (inventor,
        INVENTOR), whatever the case."""
        cad_name = (cad_name or "").strip()
        if not cad_name:
            return []
        cad = self.env["plm.cad"].sudo().find_cad(cad_name)
        names = sorted({name for name in (cad_name, cad.name, cad.code) if name})
        return ["|"] * (len(names) - 1) + [("convrsion_rule.cad_name", "=ilike", name) for name in names]

    def _cad_agent_lock_values(self, hostname, hostpws, document):
        return {
            "cad_agent_state": "downloaded",
            "cad_download_date": fields.Datetime.now(),
            "cad_upload_date": False,
            "cad_hostname": hostname,
            "cad_hostpws": hostpws,
            "workstation_id": self.env.context.get("cad_agent_workstation_id") or False,
            "cad_download_engineering_state": document.engineering_state,
            "cad_checkout_id": False,
            "error_string": False,
        }

    def _cad_version_lock(self, hostname, hostpws):
        """Take the row for the agent. A draft document is checked out to the
        workstation; a document in another state cannot be checked out by
        anyone, so it gets no check-out.
        :return True when the row is taken, False when it stays as it is
        """
        self.ensure_one()
        document = self._cad_agent_document()
        if not document:
            self.write({"cad_agent_state": "error", "error_string": _("The row has no document.")})
            return False
        if self.cad_version_target and document.cad_version == self.cad_version_target:
            self.write(
                {
                    "cad_agent_state": "done",
                    "conversion_done": True,
                    "error_string": _("The document is already at CAD version %s.", self.cad_version_target),
                }
            )
            return False
        if self.env["plm.checkout"].sudo().search_count([("documentid", "=", document.id)]):
            # checked out by a user: it stays to do, for a later batch
            return False
        values = self._cad_agent_lock_values(hostname, hostpws, document)
        if document.engineering_state == DRAFT_STATE:
            try:
                with self.env.cr.savepoint():
                    with document._cad_touched_documents()._cad_keep_write_info():
                        checkout = (
                            self.env["plm.checkout"]
                            .sudo()
                            .create(
                                {
                                    "userid": self.env.uid,
                                    "hostname": hostname,
                                    "hostpws": hostpws,
                                    "documentid": document.id,
                                }
                            )
                        )
            except Exception as ex:
                _logger.warning("CAD version update: unable to check out document %s: %s", document.id, ex)
                self.write(
                    {"cad_agent_state": "error", "error_string": _("Unable to check out the document: %s", ex)}
                )
                return False
            values["cad_checkout_id"] = checkout.id
        self.write(values)
        return True

    def _cad_export_existing_documents(self):
        """The documents already converted from the starting document in the
        end format of the row: its ExtraTree children with that extension."""
        self.ensure_one()
        document = self._cad_agent_document()
        extension = (self.convrsion_rule.end_format or "").lower()
        relations = (
            self.env["ir.attachment.relation"]
            .sudo()
            .search([("parent_id", "=", document.id), ("link_kind", "=", EXTRA_LINK_KIND)])
        )
        return relations.mapped("child_id").filtered(
            lambda child: extension and (child.name or "").lower().endswith(extension)
        )

    def _cad_export_lock(self, hostname, hostpws):
        """Take the conversions of one starting document for the agent. The
        starting document is only read, so nothing is checked out; while it or
        one of its converted documents is checked out by a user the rows stay
        to do: the check-in of the user converts them again anyway.
        :return True when the rows are taken, False when they stay as they are
        """
        document = self[:1]._cad_agent_document()
        if not document:
            self.write({"cad_agent_state": "error", "error_string": _("The row has no document.")})
            return False
        checked = document
        for row in self:
            checked |= row._cad_export_existing_documents()
        if self.env["plm.checkout"].sudo().search_count([("documentid", "in", checked.ids)]):
            return False
        self.write(self._cad_agent_lock_values(hostname, hostpws, document))
        return True

    def _cad_agent_batch_data(self):
        """The rows taken and every file they need: the document of each row
        and all the files it references.
        role of a file: "update" for the document of a CAD version update,
        the agent uploads it back; "convert" for the starting document of a
        conversion, only read; "reference" for the other files, only read.
        A document checked out by a user is downloaded only as a reference,
        whatever its row says.
        """
        files = {}
        rows = []

        def file_dict(document, role):
            return {
                "document_id": document.id,
                "name": document.name,
                "engineering_code": document.engineering_code,
                "engineering_revision": document.engineering_revision,
                "document_type": document.document_type,
                "engineering_state": document.engineering_state,
                "is_library": document.is_library,
                "library_path": document.library_path or "",
                "checksum": document.checksum,
                "role": role,
                "stack_ids": [],
            }

        for row in self:
            document = row._cad_agent_document()
            row_data = {
                "stack_id": row.id,
                "operation_type": row.operation_type,
                "document_id": document.id,
                "name": document.name,
            }
            if row.operation_type == CAD_VERSION_OPERATION:
                row_data["cad_version_target"] = row.cad_version_target
                role = "update"
            else:
                rule = row.convrsion_rule
                row_data.update(
                    {
                        "cad_name": rule.cad_name,
                        "start_format": rule.start_format,
                        "end_format": rule.end_format,
                        "cad_export_mode": rule.cad_export_mode,
                        "model_states": row._cad_export_model_states(),
                        "documents": [
                            {
                                "document_id": converted.id,
                                "name": converted.name,
                                "engineering_code": converted.engineering_code,
                            }
                            for converted in row._cad_export_existing_documents()
                        ],
                    }
                )
                role = "convert"
            rows.append(row_data)
            files.setdefault(document.id, file_dict(document, role))["stack_ids"].append(row.id)
        for row in self:
            document = row._cad_agent_document()
            if not document.document_type:
                # getDocBomFlatSql needs the document type
                continue
            for reference in document.getDocBomFlatSql():
                if reference.id not in files:
                    files[reference.id] = file_dict(reference, "reference")
        return {"rows": rows, "files": list(files.values())}

    # ------------------------------------------------------------------
    # Upload and report
    # ------------------------------------------------------------------

    def _cad_agent_check_downloaded(self):
        self.ensure_one()
        if self.operation_type not in CAD_AGENT_OPERATIONS or self.cad_agent_state != "downloaded":
            raise UserError(_("The row %s is not waiting for an upload.", self.id))

    def _cad_version_upload_refusal(self):
        """Why the updated file cannot replace the document, False when it can."""
        self.ensure_one()
        document = self._cad_agent_document()
        checkouts = self.env["plm.checkout"].sudo().search([("documentid", "=", document.id)])
        if self.cad_download_engineering_state == DRAFT_STATE:
            if not self.cad_checkout_id or checkouts != self.cad_checkout_id:
                return _("The check-out of the update on the document was removed.")
            if document.has_error:
                return _("The document has a saving error.")
        elif checkouts:
            return _("The document was checked out by %s during the update.", checkouts[0].userid.name)
        if document.engineering_state != self.cad_download_engineering_state:
            return _(
                "The state of the document changed from %(old)s to %(new)s during the update.",
                old=self.cad_download_engineering_state,
                new=document.engineering_state,
            )
        return False

    def cad_agent_upload(self, content, cad_version=False, variant=""):
        """Upload a file the agent produced for the row.
        CAD version update: the updated file replaces the document and the
        row is done.
        Conversion: the converted file updates the converted document with
        its code, or creates it; the row stays downloaded until the agent
        reports it done, as one conversion can give several files (one per
        model state).
        Neither the modification date of an existing document nor its last
        CAD save change: the file gets an "upgraded" CAD event instead.
        :content the file (bytes)
        :cad_version CAD version update: the version the file was saved
            with, the target when empty
        :variant conversion: the model state the file was exported from,
            empty for the default one
        :return (state of the row, message)
        """
        self.ensure_one()
        self._cad_agent_check_downloaded()
        if not content:
            raise UserError(_("The uploaded file is empty."))
        if self.operation_type == CONVERT_OPERATION:
            return self._cad_export_upload(content, variant)
        refusal = self._cad_version_upload_refusal()
        if refusal:
            self._cad_agent_close("skipped", refusal)
            return "skipped", refusal
        document = self._cad_agent_document()
        version = cad_version or self.cad_version_target
        with document._cad_keep_write_info():
            # no odooPLM context: a plain write, without the PLM checks;
            # no backup: a new backup would make checkNewer report the
            # document as not aligned with its last CAD save
            document.with_context(odooPLM=False, backup=False).write(
                {
                    "raw": content,
                    "cad_version": version,
                    "cad_version_update_date": fields.Datetime.now(),
                }
            )
            self._cad_agent_upgraded_event(document)
            document.message_post(body=_("File updated to CAD version %s by the CAD version update.", version))
        self._cad_agent_close("done")
        return "done", ""

    def _cad_agent_upgraded_event(self, document):
        self.env["plm.cad.open"].sudo().create(
            {
                "plm_backup_doc_id": document.getLastBackupDoc().id,
                "userid": self.env.uid,
                "document_id": document.id,
                "pws_path": self.cad_hostpws,
                "hostname": self.cad_hostname,
                "operation_type": UPGRADED_OPERATION,
            }
        )

    def _cad_export_names(self, variant=""):
        """Code and file name of the converted document, as the client names
        it at check-in (CustomProcedure applicationHook_alternative_check_file_format):
        - one file: <starting file without extension>[-<model state>]_<ext>
        - one file per model state: the same, with the model state
        - flat pattern: <starting file name without dots>_<ext>
        The dots of the name are removed from the code.
        :return (engineering code, file name)
        """
        self.ensure_one()
        document = self._cad_agent_document()
        rule = self.convrsion_rule
        end_format = (rule.end_format or "").lower()
        extension = end_format.lstrip(".")
        if rule.cad_export_mode == "flat_pattern":
            if variant:
                raise UserError(_("A flat pattern has no model state."))
            code = "%s_%s" % (document.name.replace(".", ""), extension)
            return code, document.name + end_format
        stem = os.path.splitext(document.name)[0]
        if variant:
            stem = "%s-%s" % (stem, variant)
        code = "%s_%s" % (stem.replace(".", ""), extension)
        if variant:
            return code, stem + end_format
        return code, code + end_format

    def _cad_export_upload_refusal(self):
        """Why a converted file cannot be saved, False when it can."""
        self.ensure_one()
        document = self._cad_agent_document()
        checkout = self.env["plm.checkout"].sudo().search([("documentid", "=", document.id)], limit=1)
        if checkout:
            return _("The document was checked out by %s during the conversion.", checkout.userid.name)
        return False

    def _cad_export_upload(self, content, variant=""):
        refusal = self._cad_export_upload_refusal()
        if refusal:
            self._cad_agent_close("skipped", refusal)
            return "skipped", refusal
        document = self._cad_agent_document()
        code, file_name = self._cad_export_names(variant)
        attachment = self.env["ir.attachment"].sudo().with_context(odooPLM=False)
        existing = attachment.search(
            [("engineering_code", "=", code), ("engineering_revision", "=", CONVERTED_REVISION)]
        )
        if len(existing) > 1:
            raise UserError(_("More documents have the code %s: the conversion cannot choose one.", code))
        checkout = self.env["plm.checkout"].sudo().search([("documentid", "in", existing.ids)], limit=1)
        if checkout:
            message = _("The document %(code)s is checked out by %(user)s.", code=code, user=checkout.userid.name)
            self._cad_agent_close("skipped", message)
            return "skipped", message
        with (existing | document)._cad_keep_write_info():
            converted = attachment._save_extra_file(
                content,
                code,
                doc_rev=CONVERTED_REVISION,
                file_name=existing.name or file_name,
                related_attachment_id=document.id,
            )
            if existing:
                self._cad_agent_upgraded_event(converted)
                converted.message_post(body=_("File converted again from %s by the CAD conversion.", document.name))
        values = {"cad_export_document_ids": [(4, converted.id)]}
        if not self.end_document_id:
            values["end_document_id"] = converted.id
        self.write(values)
        return "downloaded", ""

    def cad_agent_report(self, state, message=""):
        """Close a row the agent worked.
        :state error or skipped: the agent could not work the row; done: a
            conversion is complete (a CAD version update is done by its
            upload)
        :message why
        """
        self.ensure_one()
        self._cad_agent_check_downloaded()
        allowed = ["error", "skipped"]
        if self.operation_type == CONVERT_OPERATION:
            allowed.append("done")
        if state not in allowed:
            raise UserError(_("The state %s cannot be reported.", state))
        if state == "done" and not self.cad_export_document_ids:
            raise UserError(_("No converted file was uploaded for the row %s.", self.id))
        self._cad_agent_close(state, message or "")
        return True

    def _cad_agent_release(self):
        """Remove the check-out the update holds on the document."""
        for row in self:
            if row.cad_checkout_id:
                checkout = row.cad_checkout_id.sudo()
                document = checkout.documentid
                with document._cad_touched_documents()._cad_keep_write_info():
                    checkout.unlink()

    def _cad_agent_close(self, state, message=""):
        self._cad_agent_release()
        values = {
            "cad_agent_state": state,
            "conversion_done": state == "done",
            "error_string": message or False,
            "cad_checkout_id": False,
        }
        if state == "done":
            values["cad_upload_date"] = fields.Datetime.now()
        self.write(values)

    def action_cad_agent_reset(self):
        """Put the rows back to do, removing the check-out of the update."""
        rows = self.filtered(
            lambda row: row.operation_type in CAD_AGENT_OPERATIONS
            and row.cad_agent_state
            and row.cad_agent_state != "to_do"
        )
        rows._cad_agent_release()
        rows.write(
            {
                "cad_agent_state": "to_do",
                "conversion_done": False,
                "error_string": False,
                "cad_checkout_id": False,
                "cad_download_date": False,
                "cad_upload_date": False,
                "cad_hostname": False,
                "cad_hostpws": False,
                "workstation_id": False,
                "cad_download_engineering_state": False,
                "cad_export_document_ids": [(5, 0, 0)],
            }
        )
        return True
