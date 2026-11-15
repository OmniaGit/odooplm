# -*- coding: utf-8 -*-
from contextlib import contextmanager

from odoo import api, fields, models

# plm.cad.open operation written for every file the batch updated: it is not a
# "save", so the last CAD save, the update flags and the check-in dates stay
# as they were.
UPGRADED_OPERATION = "upgraded"


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    cad_version = fields.Char(
        "CAD Version",
        readonly=True,
        index=True,
        help="CAD version the file was updated to by the CAD version update. Empty when unknown.",
    )
    cad_version_update_date = fields.Datetime(
        "CAD Version Update Date",
        readonly=True,
        copy=False,
        help="When the CAD version update replaced the file.",
    )
    cad_upload_date = fields.Datetime(
        "Last CAD Upload",
        readonly=True,
        copy=False,
        help="Last time the file was saved from the CAD. The CAD version update does not change it.",
    )

    def setupCadOpen(self, hostname="", pws_path="", operation_type="", dbthread=""):
        plm_cad_open = super().setupCadOpen(
            hostname=hostname,
            pws_path=pws_path,
            operation_type=operation_type,
            dbthread=dbthread,
        )
        if operation_type == "save" and plm_cad_open.document_id:
            # no odooPLM context: a plain write, without the PLM checks and
            # without recomputing the update flags a second time
            plm_cad_open.document_id.sudo().with_context(odooPLM=False).write(
                {"cad_upload_date": plm_cad_open.create_date}
            )
        return plm_cad_open

    @api.model
    def get_upgraded_since_open(self, document_ids, hostname, pws_path):
        """Documents updated by the CAD version update after the last open
        of the current user in the given workstation and PWS: the copy of
        their file in that PWS is the one before the update.
        :document_ids ids of the documents to check
        :hostname the client workstation
        :pws_path the client PWS
        :return [document id, ...]
        """
        if not document_ids:
            return []
        self.env["plm.cad.open"].flush_model()
        document_ids = tuple(int(document_id) for document_id in document_ids)
        self.env.cr.execute(
            """
            SELECT up.document_id
              FROM (SELECT document_id, MAX(create_date) AS upgraded_date
                      FROM plm_cad_open
                     WHERE operation_type = %s
                       AND document_id IN %s
                  GROUP BY document_id) up
         LEFT JOIN (SELECT document_id, MAX(create_date) AS open_date
                      FROM plm_cad_open
                     WHERE operation_type = 'open'
                       AND document_id IN %s
                       AND userid = %s
                       AND hostname = %s
                       AND pws_path = %s
                  GROUP BY document_id) op
                ON op.document_id = up.document_id
             WHERE op.open_date IS NULL
                OR op.open_date < up.upgraded_date
            """,
            [
                UPGRADED_OPERATION,
                document_ids,
                document_ids,
                self.env.uid,
                hostname or "",
                pws_path or "",
            ],
        )
        return [row[0] for row in self.env.cr.fetchall()]

    def _cad_touched_documents(self):
        """The documents whose modification date a check-out or a check-in of
        these documents changes: the documents themselves and the drawings
        whose update flag assign_must_update_flag writes."""
        return self | self.getRelatedLayouts()

    @contextmanager
    def _cad_keep_write_info(self):
        """Put back the modification date and user of these documents after
        the operation run inside the block, in the same transaction."""
        self.env.flush_all()
        saved = []
        if self.ids:
            self.env.cr.execute(
                "SELECT id, write_date, write_uid FROM ir_attachment WHERE id IN %s",
                [tuple(self.ids)],
            )
            saved = self.env.cr.fetchall()
        yield
        self.env.flush_all()
        for attachment_id, write_date, write_uid in saved:
            self.env.cr.execute(
                "UPDATE ir_attachment SET write_date = %s, write_uid = %s WHERE id = %s",
                [write_date, write_uid, attachment_id],
            )
        self.invalidate_recordset(["write_date", "write_uid"])
