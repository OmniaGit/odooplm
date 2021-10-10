# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
Created on 24 Jul 2017

@author: dsmerghetto
'''
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    plm_document_action_syncronize_ids = fields.One2many('plm.document.action.syncronize',
                                                         inverse_name='ir_attachment_id')

    count_plm_document_action_syncronize = fields.Integer(compute='_count_plm_document_action_syncronize_ids_count',
                                                          string="S.N",
                                                          help="""Number of syncronization action to be performed in order to have the document aligned in all the servers""")

    def _count_plm_document_action_syncronize_ids_count(self):
        """
        get All version product_tempate based on this one
        """
        for ir_attachment_id in self:
            ir_attachment_id.count_plm_document_action_syncronize = 0 or self.env['plm.document.action.syncronize'].search_count([('ir_attachment_id', '=', ir_attachment_id.id),
                                                                                                                                  ('done', '=', False)])

    @api.model
    def thereIsPendingSyncronizations(self, plm_remote_server_id):
        if plm_remote_server_id:
            return self.env['plm.document.action.syncronize'].search_count([('ir_attachment_id', '=', self.id),
                                                                            ('plm_remote_server_id', '=', plm_remote_server_id.id),
                                                                            ('done', '=', False)]) != 0
        else:
            raise Exception("Try to look for a server but is not present in odoo")

    @api.model
    def full_path(self):
        return self._full_path(self.store_fname)

    @api.model
    def create_server_syncronize(self, args):
        document_id, from_server = args
        plm_document_action_syncronize = self.env['plm.document.action.syncronize']
        for plm_remote_server_id in self.env['plm.remote.server'].search([]):
            action = False
            if from_server == 'odoo':
                action = 'push'
            elif plm_remote_server_id.name == from_server:
                action = 'pull'
            val = {'plm_remote_server_id': plm_remote_server_id.id,
                   'ir_attachment_id': document_id,
                   'action': action}
            if action:
                plm_document_action_syncronize.create(val)
            else:
                raise UserError("unable to find a correct action to perform the syncronization %s" % document_id)
        return True

    @api.model
    def _isDownloadableFromServer(self, server_name):
        """
            Check in the file is downloadable from server
        """
        plm_remote_server_id = self.env["plm.remote.server"].search([('name', '=', server_name)])
        pending_syncronization = self.thereIsPendingSyncronizations(plm_remote_server_id)
        if not pending_syncronization:
            if not plm_remote_server_id.document_is_there(self.id):
                self.create_server_syncronize((self.id,
                                               'odoo'))
                return False, "Document %r is no syncronized on server %s " % (self.name,
                                                                               server_name)
            return True, ''
        else:
            return False, "Document %r is no syncronized on server %s " % (self.name,
                                                                           server_name)

    def canCheckOut(self, showError=False):
        ret = super(IrAttachment, self).canCheckOut(showError=showError)
        for plm_document_action_syncronize_id in self.plm_document_action_syncronize_ids:
            if not plm_document_action_syncronize_id.done:
                msg = _("Unable to check-Out a document that is not syncronized")
                if showError:
                    raise UserError(msg)
                else:
                    logging.error(msg)
        return ret

    def open_related_action_syncronize(self):
        return {'name': _('Sync.Actions'),
                'res_model': 'plm.document.action.syncronize',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.plm_document_action_syncronize_ids.ids)],
                'context': {}}

    def syncronize(self):
        self.env['plm.document.action.syncronize'].syncronize(document_ids=self.ids)
