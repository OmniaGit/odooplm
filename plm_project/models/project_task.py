##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################

from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    activity_product_ids = fields.One2many(
        "product.product", "activity_task_id", string="Activite Products"
    )
