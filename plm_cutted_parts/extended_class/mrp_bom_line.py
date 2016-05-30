##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 25/mag/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
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
'''
Created on 25/mag/2016

@author: mboscolo
'''
import logging
from openerp import models, fields, api, SUPERUSER_ID, _, osv
from openerp import tools

_logger = logging.getLogger(__name__)


class mrpBomLine_templateCuttedParts(models.Model):
    _inherit = 'mrp.bom.line'
    x_leght = fields.Float("X Lenght", default=0.0)
    y_leght = fields.Float("Y Lenght", default=0.0)

mrpBomLine_templateCuttedParts()
