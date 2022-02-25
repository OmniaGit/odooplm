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
from stat import SF_ARCHIVED
'''
Created on Sep 7, 2019

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


class PlmDbthread(models.Model):
    _name = "plm.dbthread"
    _description = "Db Thread Saving Model"

    documement_name_version = fields.Char(string="Document name and version",
                                          readonly=True,
                                          index=True)
    threadCode = fields.Char("Thread Code assigned automatically",
                             readonly=True,
                             index=True)
    done = fields.Boolean("This thread is done ?",
                          readonly=True,
                          index=True)
    error_message = fields.Char("Error message",
                                readonly=True)

    @api.model
    def getNewThreadTransaction(self, list_doc):
        """
        Create all the transaction objects
        """
        threadCode = self.env.get('ir.sequence').next_by_code('plm.dbthread.progress')
        for docDict in list_doc[0]:
            name = docDict.get('engineering_document_name')
            if name:
                key = "%s_%s" % (docDict.get('engineering_document_name'), docDict.get('revisionid', 0))
                if key:
                    self.create({'documement_name_version': key,
                                 'threadCode': threadCode})
        return threadCode

    @api.model
    def cleadUpPrevious(self,
                        document_key,
                        plm_dbthread_id):
        for plm_dbthread_id in self.search([('id', '<', plm_dbthread_id),
                                            ('documement_name_version', '=', document_key),
                                            ('done', '=', False)]):
            plm_dbthread_id.done = True
            plm_dbthread_id.error_message = "Automatically close from tread %s " % self.threadCode

    @api.model
    def notifieDoneToDbThread(self, clientArgs):
        document_key, dbThread, clientException = clientArgs[0]
        for plm_dbthread_id in self.search([('documement_name_version', '=', document_key),
                                            ('threadCode', '=', dbThread),
                                            ('done', '=', False)]):
            plm_dbthread_id.done = True
            if clientException:
                plm_dbthread_id.error_message = clientException
            self.cleadUpPrevious(document_key, plm_dbthread_id.id)
            return True
        logging.warning("Try to update %s but not found in the db" % clientArgs[0])
        return False

    @api.model
    def freezeDbThread(self, clientArgs):
        dbThread, error = clientArgs[0]
        for plm_dbthread_id in self.search([('threadCode', '=', dbThread),
                                            ('done', '=', False)]):
            plm_dbthread_id.done = True
            plm_dbthread_id.error_message = error
        return True

    @api.model
    def getErrorMissingDocument(self, clientArgs):
        out = []
        threadCode = clientArgs[0]
        for plm_dbthread_id in self.search([('threadCode', '=', threadCode),
                                            ('done', '=', True),
                                            ('error_message', '!=', False)]):
            out.append(plm_dbthread_id.documement_name_version)
        return out
    
    