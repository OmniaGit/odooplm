# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2020 https://OmniaSolutions.website
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
Created on 13 Nov 2020

@author: mboscolo
'''
import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class PlmComponentDocumentRel(models.Model):
    _inherit = 'plm.component.document.rel'
     
    has_web3d = fields.Boolean(string='Has Web3d',
                                       related='document_id.has_web3d',
                                       help="Check if this document has releted 3d web document")
    def show_releted_3d(self):
        for PlmCompDocRel in self:
            if PlmCompDocRel.has_web3d:
                url = PlmCompDocRel.documeent_id.get_url_for_3dWebModel()
                return {'name': 'Go to website 3dWebView',
                        'res_model': 'ir.actions.act_url',
                        'type': 'ir.actions.act_url',
                        'target': self,
                        'url': url
                        }
    
    
    
    