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
import plm_finishing
import plm_material
import product_template_extension
import plm_descriptions             # Has to be before "product_product_extension" due to related field
import product_product_extension    # Has to be before "plm_document" due to related field
import plm_document                 # Has to be before "plm_document_relations" due to related field
import plm_document_relations
import product_product_document_rel
import product_product_kanban
import plm_backup_document
import plm_checkout
import plm_config_settings
import mrp_bom_extension
import mrp_bom_line_extension
import mrp_production_extension
import document_report
