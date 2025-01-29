# -*- coding: utf-8 -*-
from odoo import api, models


class HrHolidaySummaryReport(models.AbstractModel):
    _name = 'report.plm.product_change_impact_report_template'
    _description = 'product change impact report'

    @api.model
    def _get_report_values(self, docids, data=None):
        productobj = self.env['product.product']
        attachmentobj = self.env['ir.attachment']
        bomobj = self.env['mrp.bom']

        product_change_impact_report = self.env['ir.actions.report']._get_report_from_name('plm.product_change_impact_report_template')
        if data:
            affect_product_ids = []
            affect_attachment_ids = []
            affect_bom_ids = []
            prt_datas = data.get("prt_datas", {})
            product_id = productobj.browse(data['active_id'])
            for product_data in prt_datas:
                affect_product_ids.append(productobj.browse(prt_datas[product_data].get("id")))
                affect_attachment_ids.extend(attachmentobj.browse(prt_datas[product_data].get("linkeddocuments", [])))
                affect_bom_ids.extend(bomobj.browse(prt_datas[product_data].get("bom_ids", [])))

            return {
                'doc_ids': product_id,
                'doc_model': product_change_impact_report.model,
                'affect_product_ids': affect_product_ids,
                'affect_attachment_ids': affect_attachment_ids,
                'affect_bom_ids': affect_bom_ids,
            }

        return {
            'doc_ids': docids,
            'doc_model': product_change_impact_report.model,
        }
