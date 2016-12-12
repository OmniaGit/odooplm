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
Created on 11 Aug 2016

@author: Daniel Smerghetto
'''
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID
from odoo import models
from odoo import fields
from odoo import osv
from odoo import api
from odoo import _
import time
import logging
import os
import stat


class PlmBackupDocument(models.Model):
    '''
        Only administrator is allowed to remove elements by this table
    '''
    _name = 'plm.backupdoc'

    userid = fields.Many2one('res.users',
                             _('Related User'))
    createdate = fields.Datetime(_('Date Created'),
                                 default=time.strftime("%Y-%m-%d %H:%M:%S"),
                                 readonly=True)
    existingfile = fields.Char(_('Physical Document Location'),
                               size=1024)
    documentid = fields.Many2one('plm.document',
                                 _('Related Document'))
    revisionid = fields.Integer(related="documentid.revisionid",
                                string=_("Revision"),
                                store=True)
    state = fields.Selection(related="documentid.state",
                             string=_("Status"),
                             store=True)
    document_name = fields.Char(related="documentid.name",
                                string=_("Stored Name"),
                                store=True)
    printout = fields.Binary(_('Printout Content'))
    preview = fields.Binary(_('Preview Content'))

    @api.multi
    def unlink(self):
        committed = False
        if self.env.context:
            if self.env.uid != SUPERUSER_ID:
                logging.warning("unlink : Unable to remove the required documents. You aren't authorized in this context.")
                raise UserError(_("Unable to remove the required document.\n You aren't authorized in this context."))
                return False
        documentType = self.env['plm.document']
        for checkObj in self:
            if not int(checkObj.documentid):
                return super(PlmBackupDocument, self).unlink()
            currentname = checkObj.documentid.store_fname
            if checkObj.existingfile != currentname:
                fullname = os.path.join(documentType._get_filestore(), checkObj.existingfile)
                if os.path.exists(fullname):
                    if os.path.exists(fullname):
                        os.chmod(fullname, stat.S_IWRITE)
                        os.unlink(fullname)
                        committed = True
                else:
                    logging.warning("unlink : Unable to remove the document (" + str(checkObj.documentid.name) + "-" + str(checkObj.documentid.revisionid) + ") from backup set. You can't change writable flag.")
                    raise UserError(_("Unable to remove the document (" + str(checkObj.documentid.name) + "-" + str(checkObj.documentid.revisionid) + ") from backup set.\n It isn't a backup file, it's original current one."))
        if committed:
            return super(PlmBackupDocument, self).unlink()
        else:
            return False

PlmBackupDocument()


class BackupDocWizard(osv.osv.osv_memory):
    '''
        This class is called from an action in xml located in plm.backupdoc.
        Pay attention! You can restore also confirmed, released and obsoleted documents!!!
    '''

    _name = 'plm.backupdoc_wizard'

    @api.multi
    def action_restore_document(self):
        def cleanAndLog(message, documentId, values, toRemove=[]):
            for fieldName in toRemove:
                if fieldName in values:
                    del values[fieldName]
            message = message + ' documentId: %r, values: %r' % (documentId, values)
            logging.info(message)

        documentId = False
        backupDocIds = self.env.context.get('active_ids', [])
        backupDocObj = self.env['plm.backupdoc']
        plmDocObj = self.env['plm.document']
        if len(backupDocIds) > 1:
            raise UserError(_('Restore Document Error'), _("You can restore only a document at a time."))
        for backupDocBrws in backupDocObj.browse(backupDocIds):
            relDocBrws = backupDocBrws.documentid
            values = {'printout': backupDocBrws.printout,
                      'store_fname': backupDocBrws.existingfile,
                      'preview': backupDocBrws.preview,
                      }
            if relDocBrws:
                documentId = relDocBrws.id
                writeRes = relDocBrws.write(values)
                if writeRes:
                    cleanAndLog('[action_restore_document] Updated document', documentId, values, ['printout', 'preview'])
                else:
                    cleanAndLog('[action_restore_document] Updated document failed for', documentId, values, ['printout', 'preview'])
            else:
                # Note that if I don't have a document I can't relate it to it's component
                # User have to do it hand made
                values.update({'state': 'draft',
                               'revisionid': backupDocBrws.revisionid,
                               'name': backupDocBrws.document_name,
                               }
                              )
                documentId = plmDocObj.create(values)
                if documentId:
                    cleanAndLog('[action_restore_document] Created document', documentId, values, ['printout', 'preview'])
                else:
                    cleanAndLog('[action_restore_document] Create document failed for', documentId, values, ['printout', 'preview'])
        if documentId:
            return {'name': _('Document'),
                    'view_type': 'form',
                    "view_mode": 'form, tree',
                    'res_model': 'plm.document',
                    'res_id': documentId,
                    'type': 'ir.actions.act_window',
                    'domain': "[]"}
        return True

BackupDocWizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
