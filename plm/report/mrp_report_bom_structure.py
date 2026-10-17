# -*- coding: utf-8 -*-

from odoo import models


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _plm_image_component(self, product):
        """
        The product image for the image column of the BoM overview, as the
        base64 string the client puts in a data URL (False without an image).
        The column shows it 50 px wide, so the 128 px image is enough; a
        binary field value cannot go in the json answer as it is.
        """
        image = product.image_128
        return image.to_base64() if image else False

    def _get_component_data(self, parent_bom, parent_product, warehouse, bom_line, line_quantity, level, index,
                            product_info, ignore_stock=False):
        """
        Extend component data used in the BOM overview to include the component image.

        This method overrides the base implementation to add the product image
        (`image_128`) of the BOM line's product to the returned component data.
        The data is later used by the BOM overview to render component information.
        :return: Component data enriched with component image
        :rtype: dict
        """
        res = super()._get_component_data(parent_bom, parent_product, warehouse, bom_line, line_quantity, level, index,
                                          product_info, ignore_stock)
        res['image_component'] = self._plm_image_component(bom_line.product_id)

        return res

    def _get_bom_data(self, bom, warehouse, product=False, line_qty=False, bom_line=False, level=0, parent_bom=False, parent_product=False, index=0, product_info=False, ignore_stock=False, simulated_leaves_per_workcenter=False):
        """
        Extend component data used in the BOM overview to include the component image.

        This method overrides the base implementation to add the product image
        (`image_128`) of the BOM line's product to the returned component data.
        The data is later used by the BOM overview to render component information.
        :return: Component data enriched with component image
        :rtype: dict
        """
        res = super()._get_bom_data(bom, warehouse, product, line_qty, bom_line, level, parent_bom, parent_product, index, product_info, ignore_stock, simulated_leaves_per_workcenter)
        res['image_component'] = self._plm_image_component(bom.product_id)
        return res
