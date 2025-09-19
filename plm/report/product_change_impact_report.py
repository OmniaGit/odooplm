# -*- coding: utf-8 -*-
from odoo import api, models


class ProductChangeImpactReport(models.AbstractModel):
    _name = "report.plm.product_change_impact_report_template"
    _description = "product change impact report"

    def get_bom_hierarchy(self, product_id, level=0, direction="parent"):

        product = self.env["product.product"].browse(product_id)
        hierarchy = {"level": level, "product": product, "children": []}

        if direction == "parent":
            bom_lines = self.env["mrp.bom.line"].search(
                [("product_id", "=", product.id)]
            )
            for bom_line in bom_lines:
                parent_product = bom_line.bom_id.product_tmpl_id.product_variant_id
                parent_hierarchy = self.get_bom_hierarchy(
                    parent_product.id, level + 1, direction
                )
                hierarchy["children"].append(parent_hierarchy)

        return hierarchy

    @api.model
    def _get_report_values(self, docids, data=None):
        productobj = self.env["product.product"]
        attachmentobj = self.env["ir.attachment"]

        product_change_impact_report = self.env[
            "ir.actions.report"
        ]._get_report_from_name("plm.product_change_impact_report_template")
        if data:
            affect_attachment_ids = []
            prt_datas = data.get("prt_datas", {})
            product_id = productobj.browse(data["active_id"])

            hierarchy_parent = self.get_bom_hierarchy(
                product_id=data["active_id"], level=0, direction="parent"
            )

            for product_data in prt_datas:
                affect_attachment_ids.extend(
                    attachmentobj.browse(
                        prt_datas[product_data].get("linkeddocuments", [])
                    )
                )

            return {
                "doc_ids": product_id,
                "doc_model": product_change_impact_report.model,
                "hierarchy_parent": hierarchy_parent,
                "affect_attachment_ids": affect_attachment_ids,
            }

        return {
            "doc_ids": docids,
            "doc_model": product_change_impact_report.model,
        }
