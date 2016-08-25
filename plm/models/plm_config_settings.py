# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
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
Created on 25 Aug 2016

@author: Daniel Smerghetto
'''
from openerp import models
from openerp import fields


class PlmConfigSettings(models.Model):
    _name = 'plm.config.settings'
    _inherit = 'res.config.settings'

    module_plm_automatic_weight = fields.Boolean("Plm Automatic Weight")
    module_plm_cutted_parts = fields.Boolean("Plm Cutted Parts")
    module_plm_pack_and_go = fields.Boolean("Plm Pack and go")
    module_product_description_language_helper = fields.Boolean("Plm Product Description Language Helper")
    module_plm_report_language_helper = fields.Boolean("Plm Report Language Helper")

PlmConfigSettings()
