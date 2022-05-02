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
Created on 11 Aug 2016

@author: Daniel Smerghetto
"""
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import os
import stat


class PlmBackupDocument(models.Model):
    """
        Only administrator is allowed to remove elements by this table
    """
    _name = 'plm.backupdoc'
    _description = "manage your document back up"

    userid = fields.Many2one('res.users',
                             _('Related User'))
    existingfile = fields.Char(_('Physical Document Location'),
                               size=1024)
    documentid = fields.Many2one('ir.attachment',
                                 _('Related Document'))
    revisionid = fields.Integer(related="documentid.revisionid",
                                string=_("Revision"),
                                store=True)
    state = fields.Selection(related="documentid.state",
                             string=_("Status"),
                             store=True)
    document_name = fields.Char(related="documentid.engineering_document_name",
                                string=_("Stored Name"),
                                store=True)
    printout = fields.Binary(_('Printout Content'))
    preview = fields.Binary(_('Preview Content'))

    def name_get(self):
        result = []
        for r in self:
            if r.documentid and r.userid:
                name = "%s - R:%s - [%s]" % (r.documentid.engineering_document_name, r.documentid.revisionid, r.userid.display_name)
            else:
                name = "Error"
            result.append((r.id, name))
        return result

    def remaining_unlink(self):
        super(PlmBackupDocument, self).unlink()
    
    def unlink(self):
        documentType = self.env['ir.attachment']
        for plm_backup_document_id in self:
            if self.env.context:
                if not self.env.user.has_group('plm.group_plm_admin'):
                    logging.warning("unlink : Unable to remove the required documents. You aren't authorized in this context.")
                    raise UserError(_("Unable to remove the required document.\n You aren't authorized in this context."))
            if plm_backup_document_id.documentid:
                currentname = plm_backup_document_id.documentid.store_fname
                if plm_backup_document_id.existingfile != currentname:
                    fullname = os.path.join(documentType._get_filestore(), plm_backup_document_id.existingfile)
                    if os.path.exists(fullname):
                        os.chmod(fullname, stat.S_IWRITE)
                        os.unlink(fullname)
                    else:
                        logging.warning("unlink : Unable to remove the document (" + str(plm_backup_document_id.documentid.name) + "-" + str(plm_backup_document_id.documentid.revisionid) + ") from backup set. You can't change writable flag.")
                        raise UserError(_("Unable to remove the document (" + str(plm_backup_document_id.documentid.name) + "-" + str(plm_backup_document_id.documentid.revisionid) + ") from backup set.\n It isn't a backup file, it's original current one."))
                else:
                    logging.warning('Prevent to delete the active File %r' % currentname)
                    continue
            super(PlmBackupDocument, plm_backup_document_id).unlink()

    @api.model
    def getLastBckDocumentByUser(self, doc_id):
        for obj in self.search([
            ('documentid', '=', doc_id.id),
            ], order='create_date DESC', limit=1):
            return obj
        return self


class BackupDocWizard(models.TransientModel):
    """
        This class is called from an action in xml located in plm.backupdoc.
        Pay attention! You can restore also confirmed, released and obsoleted documents!!!
    """

    _name = 'plm.backupdoc_wizard'
    _description = "Back up document wizard"

    
    def action_restore_document(self):
        ctx = self.env.context.copy()
        ctx['check'] = False
        documentId = False
        backupDocIds = self.env.context.get('active_ids', [])
        backupDocObj = self.env['plm.backupdoc']
        plmDocObj = self.env['ir.attachment']
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
                writeRes = relDocBrws.sudo().with_context(ctx).write(values)
                if writeRes:
                    logging.info('[action_restore_document] Updated document %r' % (documentId))
                else:
                    logging.warning('[action_restore_document] Updated document failed for %r' % (documentId))
            else:
                # Note that if I don't have a document I can't relate it to it's component
                # User have to do it hand made
                values.update({'state': 'draft',
                               'revisionid': backupDocBrws.revisionid,
                               'name': backupDocBrws.document_name,
                               }
                              )
                documentId = plmDocObj.sudo().create(values)
                if documentId:
                    logging.info('[action_restore_document] Created document %r' % (documentId))
                else:
                    logging.warning('[action_restore_document] Create document failed for %r' % (documentId))
        
        action_vals = self.env['ir.actions.act_window']._for_xml_id('plm.plm_action_document_form')
        domain = safe_eval(action_vals.get('domain', "[]"))
        domain = expression.AND([domain, [('id', 'in', [documentId])]])
        action_vals['domain'] = domain
        return action_vals

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
