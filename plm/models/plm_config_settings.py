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


class PlmConfigSettings(models.TransientModel):
    _name = 'res.config.settings'
    _inherit = 'res.config.settings'

    module_plm_automate_normal_bom = fields.Boolean(_("Allow to create normal BOM if not exists and product are released."))
    module_plm_automatic_weight = fields.Boolean(_("Automatic weight calculation"))
    module_plm_compare_bom = fields.Boolean(_("Compare two BOM tool"))
    module_plm_cutted_parts = fields.Boolean(_("Manage BOM explosion for cutted parts"))
    module_plm_date_bom = fields.Boolean(_("Manage BOM due to date"))
    module_plm_engineering = fields.Boolean(_("Allow to use engineering BOM"))
    module_plm_pack_and_go = fields.Boolean(_("Pack and go"))
    module_plm_product_description_language_helper = fields.Boolean(_("Product Description Language Helper"))
    module_plm_report_language_helper = fields.Boolean(_("Manage Multi Language PLM reports"))
    module_plm_spare = fields.Boolean(_("Manage spare BOM and Spare Parts Manual"))
    module_plm_web_revision = fields.Boolean(_("Create new revision from WEB"))
    module_plm_auto_internalref = fields.Boolean("Populate internal reference with engineering infos")
    module_plm_automated_convertion = fields.Boolean("Activate the server convertion tool")
    module_plm_project = fields.Boolean("Activate the PLM Project connection")
    module_plm_client_customprocedure = fields.Boolean("Activate the PLM Client mapping")
    module_plm_box = fields.Boolean("PLM Box")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
