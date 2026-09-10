# -*- coding: utf-8 -*-
import base64
from datetime import datetime

from dateutil import tz
from odoo import api, models

from .book_collector import BookCollector, packDocuments
from .component_report import getEmptyDocument


class ReportDoc2DPdf(models.AbstractModel):
    _name = "report.plm.doc_2d_pdf"
    _description = "Merge the 2D documents found in a document's structure into one PDF"

    def commonInfos(self):
        docRepository = self.env["ir.attachment"]._get_filestore()
        to_zone = tz.gettz(self.env.context.get("tz", "Europe/Rome"))
        from_zone = tz.tzutc()
        dt = datetime.now()
        dt = dt.replace(tzinfo=from_zone)
        localDT = dt.astimezone(to_zone)
        localDT = localDT.replace(microsecond=0)
        msg = "Printed by '%(print_user)s' : %(date_now)s State: %(state)s"
        msg_vals = {
            "print_user": "user_id.name",
            "date_now": localDT.ctime(),
            "state": "doc_obj.engineering_state",
        }
        mainBookCollector = BookCollector(
            jumpFirst=False,
            customText=(msg, msg_vals),
            bottomHeight=10,
            poolObj=self.env,
        )
        return docRepository, mainBookCollector

    @api.model
    def _render_qweb_pdf(self, attachment):
        docRepository, mainBookCollector = self.commonInfos()
        documents = attachment.get_2d_documents_in_doc_structure()
        if not documents:
            content = getEmptyDocument()
        else:
            documentContent = packDocuments(docRepository, documents, mainBookCollector)
            content = documentContent[0] or getEmptyDocument()
        return content

    def render_qweb_pdf(self, attachment):
        content = self._render_qweb_pdf(attachment)
        byteString = b"data:application/pdf;base64," + base64.b64encode(content)
        return byteString.decode("UTF-8")

    @api.model
    def _get_report_values(self, docids, data=None):
        attachments = self.env["ir.attachment"].browse(docids)
        return {"docs": attachments, "get_content": self.render_qweb_pdf}
