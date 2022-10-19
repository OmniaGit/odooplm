# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2022 https://OmniaSolutions.website
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
from lib2to3.pgen2.token import STAREQUAL
'''
Created on 28 Sep 2022

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

from datetime import datetime

import logging
import pytz

from odoo import api, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)

START_STATE ='draft'
RELEASED_STATUS = 'released'
OBSOLATED_STATUS = 'obsoleted'
USED_STATES = [(START_STATE, _('Draft')),
               ('confirmed', _('Confirmed')),
               (RELEASED_STATUS, _('Released')),
               ('undermodify', _('UnderModify')),
               (OBSOLATED_STATUS, _('Obsoleted'))]


class RevisionBaseMixin(models.AbstractModel):
    _name = 'revision.base.mixin'
    _inherit = ['mail.thread']
    _description = 'Revision Mixin'
    
    engineering_code = fields.Char(string="Engineering Code")
    engineering_revision = fields.Integer(string="Engineering Revision index")
    engineering_state = fields.Selection(USED_STATES,
                                         string="Engineering Status",
                                         default='draft',
                                         tracking=True)
    #
    # workflow filed to manage revisio information
    #
    engineering_release_date = fields.Datetime(_('Release date'),
                                               tracking=True)
    engineering_release_user = fields.Many2one('res.users', string=_("Release User"))
    engineering_workflow_date = fields.Datetime(_('Workflow date'),
                                                tracking=True)
    engineering_workflow_user = fields.Many2one('res.users', string=_("Workflow User"))
    
    engineering_writable = fields.Boolean('Writable',
                                          default=True)
    engineering_revision_user = fields.Many2one('res.users', string=_("User Revision"))
    engineering_revision_date = fields.Datetime(string=_('Datetime Revision'))
    _sql_constraints = [
        ('engineering_uniq', 'unique (engineering_code, engineering_revision)', _('Part Number has to be unique!'))
    ]
    
    engineering_revision_count = fields.Integer(compute='_engineering_revision_count')
    
    def _engineering_revision_count(self):
        """
        get All version product_tempate based on this one
        """
        for obj_id in self:
            if obj_id.engineering_code:
                obj_id.engineering_revision_count = self.search_count([('engineering_code', '=', obj_id.engineering_code)])
            else:
                obj_id.engineering_revision_count = 0
                
    def _mark_workflow_release_now(self):
        """
        mark the object to be released if is in the proper status
        """
        for obj in self:
            if obj.engineering_state==RELEASED_STATUS:
                obj.engineering_writable=False
                obj.engineering_release_date=datetime.now()
                obj.engineering_release_user=self.env.uid
            elif obj.engineering_state== OBSOLATED_STATUS:
                obj.engineering_writable=False
            else:
                obj.engineering_writable=True

    def _mark_worklow_user_date(self):
        for obj in self:
            obj.engineering_workflow_date=datetime.now()
            obj.engineering_workflow_user = self.env.uid
            obj._mark_workflow_release_now()
        
    def action_from_draft_to_confirmed(self):
        for obj in self:
            obj.engineering_state = 'confirmed'
            obj._mark_worklow_user_date()
    
    def action_from_confirmed_to_draft(self):
        for obj in self:
            obj.engineering_state = START_STATE
            obj._mark_worklow_user_date() 

    def action_from_confirmed_to_release(self):
        for obj in self:
            obj.engineering_state = RELEASED_STATUS
            obj._mark_worklow_user_date()
            obj._mark_obsolete_previous()
    
    def _mark_obsolare(self):
        for obj in self:
            obj.engineering_state = OBSOLATED_STATUS
            obj._mark_worklow_user_date()           
             
    def _mark_obsolete_previous(self):
        for obj in self:
            if obj.engineering_revision in [False, 0]:
                continue
            obj_previus_version = obj.get_previus_version()
            obj_previus_version._mark_obsolare()
        
    def move_to_state(self, state):
        for obj in self:
            function_name = "action_from_%s_to_%s" % (obj.engineering_state, state)
            f=getattr(obj, function_name)
            f()
        
    def is_released(self):
        self.ensure_one()
        return self.engineering_state==RELEASED_STATUS

    def new_version(self):
        """
        create a new version of the document
        """
        for obj in self:
            if obj.isReleased():
                raise UserError(_("Unable to revise a %s in status different from released" % obj._name)) 
            obj.engineering_revision+=1
            obj.engineering_state = START_STATE
            
    def copy(self, default=None):
        default = default or {}
        default['engineering_state']=START_STATE
        default['engineering_code']=False,
        default['engineering_revision']=0        
        return super(RevisionBaseMixin, self).copy(default)
        
    def get_latest_version(self):
        """
        get the latest version of this object
        """
        self.ensure_one()
        return self.search([('engineering_code','=', self.engineering_code)], order='engineering_revision DESC', limit=1)
    
    def get_previus_version(self):
        self.ensure_one()
        return self.search([('engineering_code','=', self.engineering_code),
                            ('engineering_revision','=', self.engineering_revision-1)])
                
    def get_released(self):
        self.ensure_one()
        return self.search([('engineering_code','=', self.engineering_code),
                            ('engineering_state','in',['undermodify', RELEASED_STATUS])])
            
    def get_all_revision(self):
        self.ensure_one()
        return self.search([('engineering_code','=', self.engineering_code)], order='engineering_revision DESC')
