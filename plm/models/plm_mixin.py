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
import pytz
import logging
import datetime
from datetime import datetime
from datetime import timedelta
#
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.osv import expression
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
#
_logger = logging.getLogger(__name__)
#
START_STATUS = 'draft'
CONFIRMED_STATUS = 'confirmed'
RELEASED_STATUS = 'released'
OBSOLATED_STATUS = 'obsoleted'
UNDER_MODIFY_STATUS = 'undermodify'
USED_STATES = [(START_STATUS, _('Draft')),
               (CONFIRMED_STATUS, _('Confirmed')),
               (RELEASED_STATUS, _('Released')),
               (UNDER_MODIFY_STATUS, _('UnderModify')),
               (OBSOLATED_STATUS, _('Obsoleted'))]
#
RELEASED_STATUSES = [RELEASED_STATUS,OBSOLATED_STATUS]
#
PLM_NO_WRITE_STATE = [CONFIRMED_STATUS,
                      RELEASED_STATUS,
                      UNDER_MODIFY_STATUS,
                      OBSOLATED_STATUS]
#
LOWERCASE_LETTERS = [chr(i) for i in range(ord('a'), ord('z') + 1)]
#
UPPERCASE_LETTERS = [
    chr(i) for i in range(ord('A'), ord('Z') + 1)
]
#
def convert_to_letter(l,n):
    n_o_w = len(l)
    if n > n_o_w-1:
        out = l[n_o_w-1]
        out+=convert_to_letter(n -n_o_w,l)
    else:
        out = l[n]
    return out
#
#
class RevisionBaseMixin(models.AbstractModel):
    _name = 'revision.plm.mixin'
    _inherit = ['mail.thread']
    _description = 'Revision Mixin'
    #
    engineering_code = fields.Char(string="Engineering Code")
    #
    engineering_revision = fields.Integer(string="Engineering Revision index", default=0)
    engineering_revision_letter = fields.Char(string="Engineering Revision letter", default="A")
    #
    engineering_branch_revision = fields.Integer(string="Engineering Branch index", default=0)
    engineering_branch_revision_letter = fields.Char(string="Engineering Sub Revision letter", default="A")
    #
    engineering_state = fields.Selection(USED_STATES,
                                         string="Engineering Status",
                                         default='draft',
                                         tracking=True)
    #
    # workflow filed to manage revision information
    #
    engineering_release_date = fields.Datetime(_('Release date'),
                                               tracking=True)
    engineering_release_user = fields.Many2one('res.users', string=_("Release User"))
    engineering_workflow_date = fields.Datetime(_('Workflow date'),
                                                tracking=True)
    engineering_workflow_user = fields.Many2one('res.users', string=_("Workflow User"))
    
    engineering_writable = fields.Boolean('Writable',
                                          default=True)
    engineering_code_editable = fields.Boolean("Engineering Code Editable",
                                               default=True)

    engineering_revision_user = fields.Many2one('res.users', string=_("User Revision"))
    engineering_revision_date = fields.Datetime(string=_('Datetime Revision'))
        
    engineering_branch_parent_id = fields.Integer('Parent branch')
    engineering_sub_revision_letter = fields.Char("Sub revision path")
    engineering_revision_count = fields.Integer(compute='_engineering_revision_count')
    
    # _sql_constraints = [
    #     ('engineering_uniq', 
    #      "unique (engineering_code, engineering_revision) WHERE (engineering_code is not null)",
    #      _('Part Number has to be unique!'))
    # ]

    def init(self):
        """Ensure there is at most one active variant for each combination.

        There could be no variant for a combination if using dynamic attributes.
        """
        if self._name!='revision.plm.mixin':
            sql = """
            CREATE UNIQUE INDEX IF NOT EXISTS {unique_name} 
            ON {table_name} (engineering_code, engineering_revision) 
            WHERE (engineering_code is not null or engineering_code not in ('-',''))
            """.format(unique_name="unique_index_%s"% self._table,
                       table_name=self._table)
            self.env.cr.execute(sql)
    
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
            obj.engineering_state = START_STATUS
            obj._mark_worklow_user_date() 

    def action_from_confirmed_to_released(self):
        for obj in self:
            obj.engineering_state = RELEASED_STATUS
            obj._mark_worklow_user_date()
            obj._mark_obsolete_previous()
    
    def _mark_obsolare(self):
        for obj in self:
            obj.engineering_state = OBSOLATED_STATUS
            obj._mark_worklow_user_date()           
    
    def _mark_under_modifie(self):
        for obj in self:
            obj.engineering_state = UNDER_MODIFY_STATUS
            obj._mark_worklow_user_date()
                
    def _mark_under_modifie_previous(self):
        for obj in self:
            if obj.engineering_revision in [False, 0]:
                continue
            obj_previus_version = obj.get_previus_version()
            obj_previus_version._mark_under_modifie()
            obj.message_post(body=_("New version created from Code %s Rev. %s" % (obj_previus_version.engineering_code,
                                                                                  obj_previus_version.engineering_revision)))
        
    def _mark_obsolete_previous(self):
        for obj in self:
            if obj.engineering_revision in [False, 0]:
                continue
            obj_previus_version = obj.get_previus_version()
            obj_previus_version._mark_obsolare()
    
    def before_move_to_state(self, from_state, to_state):
        """
        technical function for workflow customization
        :from_state state that came from
        :to_state state to go
        """
        self.ensure_one()
        
    def move_to_state(self, state):
        for obj in self:
            before_state = obj.engineering_state
            if before_state==state:
                logging.warning("[%s] Moving %s to %s nothing to perform" % (obj.engineering_code, state,state))
                continue
            function_name = "action_from_%s_to_%s" % (before_state, state)
            obj.before_move_to_state(before_state, state)
            f=getattr(obj, function_name)
            f()
            obj.after_move_to_state(before_state, state)       

    def after_move_to_state(self, from_state, to_state):
        """
        technical function for workflow customization
        :from_state state that came from
        :to_state state to go
        """
        self.ensure_one()
        
    def is_released(self):
        self.ensure_one()
        return self.engineering_state in [RELEASED_STATUS, UNDER_MODIFY_STATUS]
    
    def is_releaseble(self):
        self.ensure_one()
        return self.engineering_state == RELEASED_STATUS
                                          
    def new_version(self):
        """
        create a new version
        """
        for obj in self:
            if not obj.is_releaseble():
                raise UserError(_("Unable to revise a %s in status %s that different from released" % (obj.engineering_code,
                                                                                                       obj.engineering_revision)))
            obj_new = obj._new_version()
            obj_new._mark_under_modifie_previous()
            """
            "1" relased
            "2"
            #
            "1.0.3" released
            "1.0.4" draft mettere un campo che indica che una nuova versione e' stata fatta <div>
            "2"
            #
            "1.0.3" released
            "1.0.4" draft mettere un campo che indica che una nuova versione e' stata fatta <div>
            "2"
            "3"
            "3.0" ->release che deriva da 1.0.4 con replace del content del file o delle info ??
            
            #            
            """
            
    def _new_version(self):
        self.ensure_one()
        obj_latest = self.get_latest_version()
        new_revision_index = obj_latest.engineering_revision + 1
        write_context = {'name': self.name,
                         'engineering_code': self.engineering_code,
                         'engineering_revision': new_revision_index,
                         'engineering_revision_letter': self.get_revision_letter(new_revision_index),
                         'engineering_state': START_STATUS,
                         }
        obj_new = self.with_context(copy_context = write_context).copy(write_context)
        return obj_new
    
    def new_branch(self):
        """
        Make a new branch of the current object
        es:
            product_1 -> revision branch 0
            to
            product_1 -> revision branch 0.0
        """
        self._new_branch()
    
    def new_branch_version(self):
        """
        make a new version branch of the current prduct
        es:
            product_1-> revision branch 0
            to
            product_1-> revision branch 1
        """
        self._new_branch_version()
        
    def _new_branch_version(self):
        self.ensure_one()
        obj_latest = self.get_latest_version()
        new_eng_revision = obj_latest.engineering_revision + 1
        new_branch_revision = self.get_latest_level_branch_revision().engineering_branch_revision + 1
        path = ".".join(self.engineering_sub_revision_letter.split(".")[:-1])
        return self.copy({
            'engineering_revision': new_eng_revision,
            'engineering_code':obj_latest.engineering_code,
            'engineering_branch_revision': new_branch_revision,
            'engineering_sub_revision_letter': "%s.%s" % (path, new_branch_revision),
            'engineering_state': START_STATUS,
            }) 
    
    def _new_branch(self):
        self.ensure_one()
        obj_new = self._new_version()
        obj_new.engineering_branch_revision = 0 
        obj_new.engineering_branch_parent_id = self.id
        if not self.engineering_branch_parent_id:
            parnet_path = self.engineering_revision
        else:
            parnet_path = self.engineering_sub_revision_letter
        obj_new.engineering_sub_revision_letter = "%s.0" % parnet_path 
    
    def get_engineering_branch_parent(self):
        self.ensure_one()
        return self.browse(self.engineering_branch_parent_id)
        
    def get_revision_letter(self, engineering_revision=False):
        self.ensure_one()
        if engineering_revision:
            return convert_to_letter(UPPERCASE_LETTERS, engineering_revision)
        return convert_to_letter(UPPERCASE_LETTERS, self.engineering_revision)
    
    def children_branch(self):
        self.ensure_one()
        return self.search([('engineering_branch_parent_id','=', self.id)], order="engineering_branch_revision desc")
    
    def get_latest_level_branch_revision(self):
        if self.engineering_branch_parent_id:
            for children in self.search([('engineering_branch_parent_id','=', self.engineering_branch_parent_id)], order="engineering_branch_revision desc"):
                return children
        return []
        
    def copy(self, default=None):
        default = default or {}
        if 'engineering_state' not in default:
            default['engineering_state']=START_STATUS
        if 'engineering_code' not in default:
            default['engineering_code']=False
        if 'engineering_revision' not in default:
            default['engineering_revision']=0
            default['engineering_revision_letter']=self.get_revision_letter(0)             
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
                            ('engineering_revision','=', self.engineering_revision-1)], limit=1)
    
    def get_next_version(self):
        self.ensure_one()
        return self.search([('engineering_code','=', self.engineering_code),
                            ('engineering_revision','=', self.engineering_revision+1)], limit=1)
                
    def get_released(self):
        self.ensure_one()
        return self.search([('engineering_code','=', self.engineering_code),
                            ('engineering_state','in',['undermodify', RELEASED_STATUS])])
            
    def get_all_revision(self):
        self.ensure_one()
        return self.search([('engineering_code','=', self.engineering_code)], order='engineering_revision DESC')
    
    def write(self, vals):
        if 'engineering_code' in vals and vals['engineering_code'] not in [False, '-','']:
            vals['engineering_code_editable']=False
        return super(RevisionBaseMixin, self).write(vals)

    def create(self, vals):
        if 'engineering_code' in vals and vals['engineering_code'] not in [False, '-','']:
            vals['engineering_code_editable']=False
        return super(RevisionBaseMixin, self).create(vals)
        
    def get_display_notification(self, message):
        return {'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'sticky': False,
                    'type': 'info',
                }}