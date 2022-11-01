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
import logging
import datetime
from openerp import models
from openerp import fields
from openerp import api
from openerp import _
from openerp.exceptions import UserError
from datetime import timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PlmCadOpenBck(models.Model):
    _name = "plm.cad.open.bck"
    _description = "Opens made by the client"
    _order = 'id DESC'

    plm_backup_doc_id = fields.Many2one('plm.backupdoc', 'Backup Document Reference')
    userid = fields.Many2one('res.users', _('Related User'))
    document_id = fields.Many2one('plm.document', _('Related Document'))
    rel_doc_rev = fields.Integer(related='document_id.revisionid', string="Revision", store=True)
    pws_path = fields.Char(_('PWS Path'))
    hostname = fields.Char(_('Hostname'))
    operation_type = fields.Char(_('Operation Type'))
