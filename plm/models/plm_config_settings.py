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
from odoo import models
from odoo import fields
from odoo import _


class PlmConfigSettings(models.Model):
    _name = 'plm.config.settings'
    _inherit = 'res.config.settings'

    module_plm_automate_normal_bom = fields.Boolean(_("Allow to create normal BOM if not exists and product are released."))
    module_plm_automatic_weight = fields.Boolean(_("PLM Automatic Weight"))
    module_plm_compare_bom = fields.Boolean(_("Allow to compare two BOM"))
    module_plm_cutted_parts = fields.Boolean(_("Manage BOM explosion for cutted parts"))
    module_plm_date_bom = fields.Boolean(_("Manage BOM due to date"))
    module_plm_engineering = fields.Boolean(_("Allow to use engineering BOM"))
    module_plm_pack_and_go = fields.Boolean(_("PLM Pack and go"))
    module_plm_product_description_language_helper = fields.Boolean(_("Plm Product Description Language Helper"))
    module_plm_report_language_helper = fields.Boolean(_("Manage Multi Language PLM reports"))
    module_plm_spare = fields.Boolean(_("Add spare BOM and Spare Parts Manual"))
    module_plm_web_revision = fields.Boolean(_("Allow to create new revision from WEB"))

PlmConfigSettings()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
