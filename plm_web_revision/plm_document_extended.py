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
Created on 24 Jul 2017

@author: dsmerghetto
'''
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import SUPERUSER_ID
from odoo import _
import logging


class PlmDocumentExtended(models.Model):
    _name = 'document.rev_wizard'

    @api.multi
    def new_document_revision_by_server(self):
        document_id = self.env.context.get('default_document_id', False)
        if not document_id:
            logging.error('[new_document_revision_by_server] Cannot revise because document_id is %r' % (document_id))
            raise UserError(_('Current document cannot be revised!'))
        plmDocEnv = self.env['plm.document']
        docBrws = plmDocEnv.browse(document_id)
        if docBrws.document_type != 'other':
            raise UserError(_("Document cannot be revised because the document type is a CAD type document!"))
        if self.stateAllows(docBrws, 'Document'):
            newID, _newIndex = docBrws.NewRevision()
            if not newID:
                logging.error('[new_document_revision_by_server] newID: %r' % (newID))
                raise UserError(_('Something wrong happens during new document revision process.'))
            return {'name': _('Revised Document'),
                    'view_type': 'tree,form',
                    "view_mode": 'form',
                    'res_model': 'plm.document',
                    'res_id': newID,
                    'type': 'ir.actions.act_window'}

    @api.multi
    def stateAllows(self, brwsObj, objType):
        if brwsObj.state != 'released':
            logging.error('[new_document_revision_by_server:stateAllows] Cannot revise obj %s, Id: %r because state is %r' % (objType, brwsObj.id, brwsObj.state))
            raise UserError(_("%s cannot be revised because the state isn't released!" % (objType)))
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
