##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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

"""
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""

from odoo import models
from odoo import fields
from odoo import _


class PlmConfigSettings(models.TransientModel):
    _name = 'res.config.settings'
    _inherit = 'res.config.settings'

    module_plm_automate_normal_bom = fields.Boolean(
        _("Allow to create normal BOM if not exists and product are released."))
    module_plm_automatic_weight = fields.Boolean(_("Automatic weight calculation"))
    module_plm_compare_bom = fields.Boolean(_("Compare two BOM tool"))
    module_plm_cutted_parts = fields.Boolean(_("Manage BOM explosion for cut parts"))
    module_plm_date_bom = fields.Boolean(_("Manage BOM due to date"))
    module_plm_engineering = fields.Boolean(_("Allow to use engineering BOM"))
    module_plm_pack_and_go = fields.Boolean(_("Pack and go"))
    module_plm_product_description_language_helper = fields.Boolean(_("Product Description Language Helper"))
    module_plm_report_language_helper = fields.Boolean(_("Manage more Language PLM reports"))
    module_plm_spare = fields.Boolean(_("Manage spare BOM and Spare Parts Manual"))
    module_plm_web_revision = fields.Boolean(_("Create new revision from WEB"))
    module_plm_auto_internalref = fields.Boolean("Populate internal reference with engineering part number")
    module_plm_automated_convertion = fields.Boolean("Activate the server conversion tool")
    module_plm_project = fields.Boolean("Activate the PLM Project connection")
    module_plm_client_customprocedure = fields.Boolean("Activate the PLM Client mapping")
    module_plm_box = fields.Boolean("PLM Box")
    module_plm_suspended = fields.Boolean("Manage Product suspend code")
    module_plm_auto_engcode = fields.Boolean("Enable Automatic Engineering Code")
    module_plm_bom_summarize = fields.Boolean("Enable B.O.M. summarisation during the client upload")
    module_activity_validation = fields.Boolean("Enable Eco /Ecr")
    module_plm_web_3d = fields.Boolean("Enable 3D WebGl")
    module_plm_web_3d_sale = fields.Boolean("Enable 3D WebGl for e-commerce and sale")
    module_plm_breakages = fields.Boolean("Enable breakages management")
    module_plm_pdf_workorder = fields.Boolean("Enable Plm PDF document inside workorder")
    module_plm_sale_fix = fields.Boolean("Add plm groups permission to sale")
    module_plm_document_multi_site = fields.Boolean("Multi side storage system")
    module_plm_mrp_bom_update = fields.Boolean("MRP B.O.M Update")
    module_plm_product_only_latest = fields.Boolean("Force last version on Manufacturing")
    module_plm_purchase_only_latest = fields.Boolean("Force last version on purchase")
    module_plm_sale_only_latest = fields.Boolean("Force last version on Sale")
    
    
