# -*- coding: utf-8 -*-

import json

from odoo import api, models, _
from odoo.tools import float_round
import copy


class ReportProdStructure(models.AbstractModel):
    _name = 'report.plm.report_prod_structure'
    _description = 'Prod Doc Structure Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        items_to_show = {}
        product_ids = self.env['product.product'].browse(docids)
        for product_id in product_ids:
            for attachment_id in product_id.linkeddocuments:
                if attachment_id.document_type.upper() == '3D':
                    items_to_show.setdefault(attachment_id.id)
                    visible_attachments = self.checkVisibleItems(attachment_id, [])
                    items_to_show[attachment_id.id] = visible_attachments
                    vals = self.singleItem(attachment_id, 0, True, items_to_show, attachment_id)
                    docs.append(vals)
        return {'doc_ids': docids, 'doc_model': 'product.product', 'docs': docs, 'items_to_show': items_to_show,}
    
    @api.model
    def get_doc_prod(self, attachment, level=False, items_to_show={}, root_doc=False):
        data = self.singleItem(attachment, level, True, items_to_show, root_doc)
        return self.env.ref('plm.report_prod_bom_line')._render({'data': data})
    
    def checkVisibleItems(self, parent_doc, parents=[]):
        out = []
        if not parent_doc.linkedcomponents:
            out.append(parent_doc.id)
            out.extend(parents)
        children = parent_doc.getRelatedOneLevelLinks(parent_doc.id, ['RfTree', 'HiTree'])
        for child_id in children:
            attachment_child = self.env['ir.attachment'].browse(child_id)
            new_parents = copy.deepcopy(parents)
            new_parents.append(parent_doc.id)
            children_out = self.checkVisibleItems(attachment_child, new_parents)
            out.extend(children_out)
        out = list(set(out))
        return out
    
    def singleItem(self, attachment, level=0, recursion=True, items_to_show={}, root_doc=False):
        children_list = []
        visible = False
        visible_items = items_to_show.get(root_doc.id, [])
        if attachment.id in visible_items:
            visible = True
        if recursion and attachment.document_type.upper() == '3D':
            children = attachment.getRelatedOneLevelLinks(attachment.id, ['RfTree', 'LyTree', 'HiTree'])
            for child_id in children:
                attachment_child = self.env['ir.attachment'].browse(child_id)
                child_dict = self.singleItem(attachment_child, level + 1, False, items_to_show, root_doc)
                children_list.append(child_dict)
        vals = {'id': attachment, 'level': level, 'report_obj': self, 'children': children_list, 'visible': visible, 'items_to_show': items_to_show}
        return vals
