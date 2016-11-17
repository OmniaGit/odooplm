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
Created on 25 Aug 2016

@author: Daniel Smerghetto
'''
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import time


class PlmCheckout(models.Model):
    _name = 'plm.checkout'

    userid = fields.Many2one('res.users',
                             _('Related User'),
                             ondelete='cascade')
    hostname = fields.Char(_('hostname'),
                           size=64)
    hostpws = fields.Char(_('PWS Directory'),
                          size=1024)
    documentid = fields.Many2one('plm.document',
                                 _('Related Document'),
                                 ondelete='cascade')
    createdate = fields.Datetime(_('Date Created'),
                                 default=time.strftime("%Y-%m-%d %H:%M:%S"),
                                 readonly=True)
    rel_doc_rev = fields.Integer(related='documentid.revisionid',
                                 string="Revision",
                                 store=True)

    _sql_constraints = [
        ('documentid', 'unique (documentid)', _('The documentid must be unique !'))
    ]

    @api.model
    def _adjustRelations(self, childDocIds, userid=False):
        docRelType = self.env['plm.document.relation']
        if userid:
            docRelBrwsList = docRelType.search([('child_id', 'in', childDocIds), ('userid', '=', False)])
        else:
            docRelBrwsList = docRelType.search([('child_id', 'in', childDocIds)])
        if docRelBrwsList:
            values = {'userid': userid}
            docRelBrwsList.write(values)

    @api.model
    def create(self, vals):
        docBrws = self.env['plm.document'].browse(vals['documentid'])
        values = {'writable': True}
        if not docBrws.write(values):
            logging.warning("create : Unable to check-out the required document (" + str(docBrws.name) + "-" + str(docBrws.revisionid) + ").")
            raise UserError(_("Unable to check-out the required document (" + str(docBrws.name) + "-" + str(docBrws.revisionid) + ")."))
        self._adjustRelations([docBrws.id])
        newCheckoutBrws = super(PlmCheckout, self).create(vals)
        docBrws.wf_message_post(body=_('Checked-Out'))
        return newCheckoutBrws

    @api.multi
    def unlink(self):
        documentType = self.env['plm.document']
        docids = []
        for checkObj in self:
            checkObj.documentid.writable = False
            values = {'writable': False}
            docids.append(checkObj.documentid.id)
            if not documentType.browse([checkObj.documentid.id]).write(values):
                logging.warning("unlink : Unable to check-in the document (" + str(checkObj.documentid.name) + "-" + str(checkObj.documentid.revisionid) + ").\n You can't change writable flag.")
                raise UserError(_("Unable to Check-In the document (" + str(checkObj.documentid.name) + "-" + str(checkObj.documentid.revisionid) + ").\n You can't change writable flag."))
        self._adjustRelations(docids, False)
        dummy = super(PlmCheckout, self).unlink()
        if dummy:
            documentType.browse(docids).wf_message_post(body=_('Checked-In'))
        return dummy

PlmCheckout()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
