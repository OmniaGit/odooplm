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
import os
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
    _description = "PLM Client Support object"

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
        ir_attachemnt = self.env['ir.attachment']
        for doc_id in ir_attachemnt.browse(ir_attachemnt_id):
            outIds.extend(doc_id.computeDownloadStatus(hostname, pws_path))
            if doc_id.is2D():
                outIds.extend(ir_attachemnt.browse(ir_attachemnt.getRelatedLyTree(doc_id.id)).computeDownloadStatus(hostname, pws_path))
        outIds.extend(ir_attachemnt.browse(ir_attachemnt.getRelatedHiTree(doc_id.id, recursion=True, getRftree=True)).computeDownloadStatus(hostname,pws_path))
        return outIds
    
    def getAttachmentFromProp(self,
                              document_attributes):
        """
        Get The attachment from a dictionary
        check before from id and the from minimun property
        """
        attach_object = self.env['ir.attachment']
        attach_id = document_attributes.get('id')
        if attach_id:
            ir_browse = attach_object.browse(attach_id)
        else:
            ir_browse = attach_object.search([('engineering_document_name', '=', document_attributes.get('engineering_document_name', '')),
                                              ('revisionid', '=', document_attributes.get('revisionid', -1))]) 
        return ir_browse

    @api.model
    def attachmentCanBeSaved(self,
                             document_attributes,
                             raiseError=False,
                             returnCode=False,
                             skipCheckOutControl=False):
        
        """
        Check if the document can be saved !!
        """
        for brwItem in self.getAttachmentFromProp(document_attributes):
            return brwItem.canBeSaved(raiseError=raiseError,
                                      returnCode=returnCode,
                                      skipCheckOutControl=skipCheckOutControl)
        return True, ''

    @api.model
    def attachmentCheckOut(self,
                           document_attributes,
                           hostName,
                           hostPws, 
                           showError=True):
        """
        perform the check out operation from document attributes
        """
        for brwItem in self.getAttachmentFromProp(document_attributes):
            return brwItem.checkout(hostName=hostName,
                                    hostPws=hostPws,
                                    showError=showError)
        return True, ''    
    