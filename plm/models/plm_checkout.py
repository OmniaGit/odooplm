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

"""
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import time


class PlmCheckout(models.Model):
    _name = 'plm.checkout'
    _description = 'Document that are locked from someone'

    userid = fields.Many2one('res.users',
                             _('Related User'),
                             index=True,
                             ondelete='cascade')
    hostname = fields.Char(_('hostname'),
                           index=True,
                           size=64)
    hostpws = fields.Char(_('PWS Directory'),
                          index=True,
                          size=1024)
    documentid = fields.Many2one('ir.attachment',
                                 _('Related Document'),
                                 index=True,
                                 ondelete='cascade')
    rel_doc_rev = fields.Integer(related='documentid.revisionid',
                                 string="Revision",
                                 store=True)

    preview = fields.Binary(related='documentid.preview')

    _sql_constraints = [
        ('documentid', 'unique (documentid)', _('The documentid must be unique !'))
    ]

    
    def name_get(self):
        result = []
        for r in self:
            if not r.documentid or not r.userid:
                name = 'unknown'
            else:
                document_name = r.documentid.name if r.documentid.engineering_document_name is False else r.documentid.engineering_document_name
                name = "%s .. [%s]" % (document_name[:10], r.userid.name[:8])
            result.append((r.id, name))
        return result

    @api.model
    def _adjustRelations(self, childDocIds, userid=False):
        docRelType = self.env['ir.attachment.relation']
        if userid:
            docRelBrwsList = docRelType.search([('child_id', 'in', childDocIds), ('userid', '=', False)])
        else:
            docRelBrwsList = docRelType.search([('child_id', 'in', childDocIds)])
        if docRelBrwsList:
            values = {'userid': userid}
            docRelBrwsList.write(values)

    @api.model
    def create(self, vals):
        docBrws = self.env['ir.attachment'].browse(vals['documentid'])
        values = {'writable': True}
        if not docBrws.sudo(True).write(values):
            logging.warning("create : Unable to check-out the required document (" + str(docBrws.engineering_document_name) + "-" + str(docBrws.revisionid) + ").")
            raise UserError(_("Unable to check-out the required document (" + str(docBrws.engineering_document_name) + "-" + str(docBrws.revisionid) + ")."))
        self._adjustRelations([docBrws.id])
        newCheckoutBrws = super(PlmCheckout, self).create(vals)
        docBrws.wf_message_post(body=_('Checked-Out ID %r' % (newCheckoutBrws.id)))
        return newCheckoutBrws

    
    def unlink(self):
        documentType = self.env['ir.attachment']
        docids = []
        for checkObj in self:
            if not checkObj.documentid:
                continue
            checkObj.documentid.writable = False
            values = {'writable': False}
            docids.append(checkObj.documentid.id)
            if not documentType.browse([checkObj.documentid.id]).write(values):
                logging.warning("unlink : Unable to check-in the document (" + str(checkObj.documentid.engineering_document_name) + "-" + str(checkObj.documentid.revisionid) + ").\n You can't change writable flag.")
                raise UserError(_("Unable to Check-In the document (" + str(checkObj.documentid.engineering_document_name) + "-" + str(checkObj.documentid.revisionid) + ").\n You can't change writable flag."))
        self._adjustRelations(docids, False)
        dummy = super(PlmCheckout, self).unlink()
        if dummy:
            documentType.browse(docids).wf_message_post(body=_('Checked-In'))
        return dummy


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
