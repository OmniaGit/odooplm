##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2020 OmniaSolutions (<https://omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# Leonardo Cazziolati
# leonardo.cazziolati@omniasolutions.eu
# 23-06-2020

from odoo import models
from odoo import fields
from odoo import api
from odoo import _

class PlmBreakages(models.Model):
    _name = 'plm.breakages'
    _description = 'PLM Breakages'
    _inherit = 'mail.thread'
    
    name = fields.Char(readonly=True, required=True, copy=False, default="New")
    product_id = fields.Many2one("product.product","Product")
    parent_id = fields.Many2one("product.product","Parent")
    partner_id = fields.Many2one("res.partner","Customer")
    lot_number = fields.Char("Lot/Serial Number")
    date = fields.Date('Date', required=True, copy=False, default=fields.Date.today)
    notes = fields.Text("Notes")
    tracking = fields.Selection(related = 'product_id.tracking')
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            vals['name'] = self.env['ir.sequence'].next_by_code('plm.breakages', sequence_date=seq_date) or '/'
        return super(PlmBreakages, self).create(vals)
    
    