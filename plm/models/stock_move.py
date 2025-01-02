# -*- coding: utf-8 -*-
from odoo import _, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    engineering_revision = fields.Integer(related="product_id.engineering_revision",
                                          string=_("Revision"),
                                          help=_("The revision of the product."))
    engineering_state = fields.Selection(related="product_id.engineering_state",
                                         string=_("Status"),
                                         help=_("The status of the product in its LifeCycle."),
                                         store=False)
