# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''
Created on Sep 7, 2019

@author: mboscolo
'''
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import os
import logging
import base64
import json


class PlmConvertFormat(models.Model):
    _name = "plm.convert.format"
    _description = "Convert Format"
    _order = 'sequence ASC'

    sequence = fields.Integer('Sequence', default="1")
    name = fields.Char("Format Name", compute="_compute_name")
    available = fields.Boolean('Available for conversion')
    start_format = fields.Char('Start Format', required=True)
    end_format = fields.Char('End Format', required=True)
    cad_name = fields.Char('Cad Name', required=True)
    server_id = fields.Many2one('plm.convert.servers',
                                string='Server',
                                required=True)
    def _compute_name(self):
        for plm_convert_format in self:
            plm_convert_format.name = "%s %s %s %s" % (plm_convert_format.server_id.name or "",
                                                       plm_convert_format.cad_name,
                                                       plm_convert_format.name,
                                                       plm_convert_format.end_format) 
        
        
        
    
    
