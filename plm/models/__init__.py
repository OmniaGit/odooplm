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
from . import base
from . import product_product_document_rel
from . import plm_treatment
from . import plm_finishing
from . import plm_material
from . import product_template
from . import plm_descriptions             # Has to be before "product_product_extension" due to related field
from . import product_product              # Has to be before "ir_attachment" due to related field
from . import ir_attachment                # Has to be before "ir_attachment_relations" due to related field
from . import ir_attachment_relations
from . import product_product_kanban
from . import plm_backup_document
from . import plm_checkout
from . import res_config_settings
from . import mrp_bom
from . import mrp_bom_line
from . import report_on_document
from . import plm_temporary
from . import plm_dbthread
from . import res_users
from . import plm_cad_open
from . import ir_ui_view
from . import plm_cad_open_bck
from . import mail_activity_type
from . import plm_client
from . import res_groups
