# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solution
#    Copyright (C) 2011-2019 https://wwww.omniasolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''
Created on Apr 6, 2019

@author: mboscolo
'''


import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class MrpProduction(models.Model):
    _inherit = 'mrp.production'      

    def update_row_line_form_bom(self):
        for mrp_production_id in self:
            if mrp_production_id.state in ['draft', 'confirmed', 'planned', 'progress']:
                new_product_id = mrp_production_id.product_id.getLatestReleasedRevision()
                if new_product_id.id != mrp_production_id.product_id.id:
                    product_done_qty = {}
                    for move_line_id in mrp_production_id.move_raw_ids + mrp_production_id.move_finished_ids:
                        product_done_qty[move_line_id.product_id.engineering_code] = move_line_id.quantity_done
                        try:
                            move_line_id.action_cancel()
                            move_line_id.unlink()
                        except Exception as ex:
                            logging.warning("Unable to perform action_cancel confirm and reserve the product")
                            move_line_id.confirm_and_reverse()    
                    mrp_production_id.product_id = new_product_id.id 
                    mrp_production_id.message_post(body="Product and BOM Updated by procedure [%s, %s]" % (new_product_id.engineering_code, new_product_id.engineering_revision))
                    mrp_production_id.onchange_product_id()
                    mrp_production_id._generate_moves()
                    for move_line_id in mrp_production_id.move_raw_ids + mrp_production_id.move_finished_ids:
                        if move_line_id.product_id.engineering_code in product_done_qty:
                            move_line_id.quantity_done = product_done_qty[move_line_id.product_id.engineering_code]
                else:
                    super(MrpProduction, self).update_row_line_form_bom()
            else:
                raise UserError("Unable to perform such operation from state %r" % self.state)

        