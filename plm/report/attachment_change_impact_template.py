# -*- coding: utf-8 -*-
from odoo import api, models


class ProductChangeImpactReport(models.AbstractModel):
    _name = "report.plm.attachment_change_impact_report_template"
    _description = "attachment change impact report"

    def get_product_hierarchy(self, product_id, level=0):

        product = self.env["product.product"].browse(product_id)
        hierarchy = {"level": level, "product": product, "children": []}

        bom_lines = self.env["mrp.bom.line"].search([("product_id", "=", product.id)])
        for bom_line in bom_lines:
            parent_product = bom_line.bom_id.product_tmpl_id.product_variant_id
            parent_hierarchy = self.get_product_hierarchy(parent_product.id, level + 1)
            hierarchy["children"].append(parent_hierarchy)

        return hierarchy

    @api.model
    def _get_report_values(self, docids, data=None):
        attachment_change_impact_report = self.env[
            "ir.actions.report"
        ]._get_report_from_name("plm.attachment_change_impact_report_template")

        if data and "active_id" in data:
            attachment_obj = self.env["ir.attachment"]
            attachment_id = attachment_obj.browse(data["active_id"])

            linked_product = attachment_id.linkedcomponents

            product_data = []
            for product in linked_product:
                product_data.append(self.get_product_hierarchy(product_id=product.id))

            return {
                "doc_ids": docids,
                "doc_model": attachment_change_impact_report.model,
                "product_data": product_data,
            }

        return {
            "doc_ids": docids,
            "doc_model": attachment_change_impact_report.model,
        }
