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
from openerp.exceptions import UserError
from openerp import models
from openerp import fields
from openerp import _
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
                                 readonly=True)
    rel_doc_rev = fields.Integer(related='documentid.revisionid',
                                 string="Revision",
                                 store=True)

    _defaults = {
        'create_date': lambda self, ctx: time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _sql_constraints = [
        ('documentid', 'unique (documentid)', _('The documentid must be unique !'))
    ]

    def _adjustRelations(self, cr, uid, oids, userid=False):
        docRelType=self.pool.get('plm.document.relation')
        if userid:
            ids=docRelType.search(cr,uid,[('child_id','in',oids),('userid','=',False)])
        else:
            ids=docRelType.search(cr,uid,[('child_id','in',oids)])
        if ids:
            values={'userid':userid,}
            docRelType.write(cr, uid, ids, values)

    def create(self, cr, uid, vals, context=None):
        documentType=self.pool.get('plm.document')
        docID=documentType.browse(cr, uid, vals['documentid'])
        values={'writable':True,}
        if not documentType.write(cr, uid, [docID.id], values):
            logging.warning("create : Unable to check-out the required document ("+str(docID.name)+"-"+str(docID.revisionid)+").")
            raise UserError( _("Unable to check-out the required document ("+str(docID.name)+"-"+str(docID.revisionid)+")."))
            return False
        self._adjustRelations(cr, uid, [docID.id], uid)
        newID = super(PlmCheckout,self).create(cr, uid, vals, context=context)   
        documentType.wf_message_post(cr, uid, [docID.id], body=_('Checked-Out'))
        return newID

    def unlink(self, cr, uid, ids, context=None):
        documentType=self.pool.get('plm.document')
        checkObjs=self.browse(cr, uid, ids, context=context)
        docids=[]
        for checkObj in checkObjs:
            checkObj.documentid.writable=False
            values={'writable':False,}
            docids.append(checkObj.documentid.id)
            if not documentType.write(cr, uid, [checkObj.documentid.id], values):
                logging.warning("unlink : Unable to check-in the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+").\n You can't change writable flag.")
                raise UserError( _("Unable to Check-In the document ("+str(checkObj.documentid.name)+"-"+str(checkObj.documentid.revisionid)+").\n You can't change writable flag."))
                return False
        self._adjustRelations(cr, uid, docids, False)
        dummy = super(PlmCheckout,self).unlink(cr, uid, ids, context=context)
        if dummy:
            documentType.wf_message_post(cr, uid, docids, body=_('Checked-In'))
        return dummy

PlmCheckout()
