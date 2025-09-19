# -*- coding: utf-8 -*-
from odoo import models


class ReportBomStructure(models.AbstractModel):
    _inherit = "report.mrp.report_bom_structure"

    def _get_component_data(
        self,
        parent_bom,
        parent_product,
        warehouse,
        bom_line,
        line_quantity,
        level,
        index,
        product_info,
        ignore_stock=False,
    ):

        res = super()._get_component_data(
            parent_bom,
            parent_product,
            warehouse,
            bom_line,
            line_quantity,
            level,
            index,
            product_info,
            ignore_stock,
        )
        res["image_component"] = bom_line.product_id.image_1920

        return res
