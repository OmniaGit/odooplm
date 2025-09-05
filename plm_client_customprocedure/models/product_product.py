# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # update_3d_file = fields.Boolean(string='Update 3D File')
    # mapping_id = fields.Many2one('odoo.cad.mapping')
    # product_old_data = fields.Char()
    #
    # def write(self, vals):
    #     tracked_fields = self.env['odoo.cad.mapping'].search([]).mapped('odoo_fields_id.name')
    #     change_logs = {}
    #     for record in self:
    #         for field in tracked_fields:
    #             if field in vals:
    #                 old_value = getattr(record, field)
    #                 new_value = vals.get(field)
    #                 if old_value != new_value:
    #                     change_logs[record.id] = change_logs.get(record.id, []) + [
    #                         f"{field}: old data ---> {old_value}    new data ---> {new_value}"
    #                     ]
    #
    #     res = super().write(vals)
    #
    #     for rec in self:
    #         if rec.id in change_logs:
    #             rec.write({
    #                 'product_old_data': "\n".join(change_logs[rec.id]),
    #                 'update_3d_file': True
    #             })
    #
    #     return res
    #
    # def _cron_auto_create_plm_convert_stack(self):
    #     """
    #     This cron action will automatically create plm convert stack
    #     record base of boolean(update_3d_file) on product model.
    #     """
    #     products_to_update = self.search([('update_3d_file', '=', True)])
    #
    #     data_to_update = []
    #     for product_id in products_to_update:
    #         attachment_id = product_id.linkeddocuments.filtered(lambda a: a.document_type == "3d")
    #         existing_record = self.env['plm.convert.stack'].search([
    #             ('start_document_id', '=', attachment_id.id),
    #             ('conversion_done', '=', False)
    #         ])
    #         if not existing_record:
    #             self.env['plm.convert.stack'].create({
    #                 'start_document_id': attachment_id.id,
    #                 'product_category': product.categ_id.id,
    #
    #             })
    #
    #     if data_to_update:
    #         self.env['plm.convert.stack'].create(data_to_update)
