# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
Created on 1 Dec 2021

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

class PlmClient(models.TransientModel):
    _name = "plm.client"
    
    @api.model
    def getFileStructure(self, ir_attachemnt_id, hostname, pws_path):
        """
        get all the relation of the passed attachment and their status
        :ir_attachment_id int id of object ir_attachment
        :hostname client host name
        :pws_path client pws path
        :return: list of [{<ir_attachment_attrivutes>}]
        """
        outIds = []
        ids_to_compute = [] 
        ir_attachemnt = self.env['ir.attachment']
        for doc_id in ir_attachemnt.browse(ir_attachemnt_id):
            ids_to_compute.append(doc_id.computeDownloadStatus(hostname, pws_path))
            if doc_id.is2D():
                outIds.extend(ir_attachemnt.getRelatedLyTree(doc_id).computeDownloadStatus(hostname, pws_path))
        outIds.extend(ir_attachemnt.getRelatedHiTree(doc_id, recursion=True, getRftree=True).computeDownloadStatus(hostname,pws_path))
        return outIds
    
    
    
    
    