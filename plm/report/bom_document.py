# -*- coding: utf-8 -*-

import json

from odoo import api, models, _
from odoo.tools import float_round

class ReportDocStructure(models.AbstractModel):
    _name = 'report.plm.report_doc_structure'
    _description = 'Doc Structure Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        for doc_id in docids:
            attachment_id = self.env['ir.attachment'].browse(doc_id)
            vals = attachment_id.getDocBom(report_obj=self)
            docs.append(vals)
        return {'doc_ids': docids, 'doc_model': 'ir.attachment', 'docs': docs}
        
    @api.model
    def get_doc_bom(self, attachment_id, level=False, parent=False):
        data = attachment_id.getDocBom(level=level, report_obj=self)
        return self.env['ir.ui.view']._render_template('plm.report_doc_bom_line', {'data': data})
