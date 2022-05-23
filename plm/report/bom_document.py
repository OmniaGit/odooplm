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
            vals = self.singleItem(attachment_id, 0, True)
            docs.append(vals)
        return {'doc_ids': docids, 'doc_model': 'ir.attachment', 'docs': docs}
        
    @api.model
    def get_doc_bom(self, attachment, level=False, parent=False):
        data = self.singleItem(attachment, level)
        return self.env.ref('plm.report_doc_bom_line')._render({'data': data})

    def singleItem(self, attachment, level, recursion=True):
        children_list = []
        if recursion and attachment.document_type.upper() not in ['2D']:
            children = attachment.getRelatedOneLevelLinks(attachment.id, ['RfTree', 'LyTree', 'HiTree'])
            for child_id in children:
                attachment_child = self.env['ir.attachment'].browse(child_id)
                child_dict = self.singleItem(attachment_child, level + 1, recursion=False)
                children_list.append(child_dict)
        vals = {'id': attachment, 'level': level, 'report_obj': self, 'children': children_list}
        return vals
