# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution    
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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

'''
Created on Mar 30, 2016

@author: Daniel Smerghetto
'''
import logging
from openerp import models, fields, api, SUPERUSER_ID, _, osv
from openerp import tools
import base64
import os
import shutil
_logger = logging.getLogger(__name__)


class product_templateCuttedParts(models.Model):
    _inherit = 'product.template'
    row_material = fields.Many2one('product.product', _("Row Material Product"))
    row_material_xlenght = fields.Float(_("Row Material x lenght"), default=0.0)
    row_material_ylenght = fields.Float(_("Row Material y_lenght"), default=0.0)
    wastage_percent = fields.Float(_("Percent Wastage"), default=0.0)
    is_row_material = fields.Boolean(_("Is Row Material"))

product_templateCuttedParts()
