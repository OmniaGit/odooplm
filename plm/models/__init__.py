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
from . import plm_finishing
from . import plm_material
from . import product_template
from . import plm_descriptions             # Has to be before "product_product_extension" due to related field
from . import product_product              # Has to be before "plm_document" due to related field
from . import plm_document                 # Has to be before "plm_document_relations" due to related field
from . import plm_document_relations
from . import product_product_document_rel
from . import product_product_kanban
from . import plm_backup_document
from . import plm_checkout
from . import plm_config_settings
from . import mrp_bom
from . import mrp_bom_line
from . import report_on_document
from . import plm_temporary
