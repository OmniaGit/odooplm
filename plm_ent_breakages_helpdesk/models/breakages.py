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
    _inherit = 'plm.breakages'
    
    ticket_ids = fields.Many2many("helpdesk.ticket",
                                   relation="omnia_breakages_ticket_rel",
                                   column1="ticket_id",
                                   column2="breakage_id",
                                   string="Ticket")
    
    