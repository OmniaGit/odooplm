# -*- coding: utf-8 -*-
from odoo import _, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    engineering_revision = fields.Integer(
        related="product_id.engineering_revision",
        string="Revision",
        help="The revision of the product.",
    )
    engineering_state = fields.Selection(
        related="product_id.engineering_state",
        string="Eng. Status",
        help="The status of the product in its LifeCycle.",
        store=False,
    )
