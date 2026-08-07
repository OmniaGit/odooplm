##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

"""
Created on 11 Aug 2016

@author: Daniel Smerghetto
"""
from odoo.tools.safe_eval import safe_eval
from odoo.fields import Domain
from odoo.exceptions import UserError, ValidationError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import os
import stat
import datetime


class PlmBackupDocument(models.Model):
    """
    Only administrator is allowed to remove elements by this table
    """

    _name = "plm.backupdoc"
    _description = "manage your document back up"

    userid = fields.Many2one("res.users", string="Related User")
    existingfile = fields.Char(string="Physical Document Location", size=1024)
    documentid = fields.Many2one("ir.attachment", string="Related Document")
    engineering_revision = fields.Integer(
        related="documentid.engineering_revision", string="Revision", store=True
    )
    engineering_state = fields.Selection(
        related="documentid.engineering_state", string="Status", store=True
    )
    document_name = fields.Char(
        related="documentid.engineering_code", string="Stored Name", store=True
    )
    printout = fields.Binary(string="Printout Content")
    preview = fields.Binary(string="Preview Content")
    orig_data_fstore = fields.Char(string="Original FStore Name")

    @api.depends('document_name')
    def _compute_display_name(self):
        """
        Compute a custom display name for Purchase Orders.
        If context has 'show_vendor', it includes the vendor name.
        Otherwise, only the order name is shown.
        """
        for rec in self:
            rec.display_name = f"{rec.documentid.engineering_code} - Rev. :{rec.documentid.engineering_revision} - [{rec.userid.display_name}]"

    def remaining_unlink(self):
        super(PlmBackupDocument, self).unlink()

    def unlink(self):
        documentType = self.env["ir.attachment"]
        for plm_backup_document_id in self:
            if self.env.context:
                if not self.env.user.has_group("plm.group_plm_admin"):
                    logging.warning(
                        "unlink : Unable to remove the required documents. You aren't authorized in this context."
                    )
                    raise UserError(
                        _(
                            "Unable to remove the required document.\n You aren't authorized in this context."
                        )
                    )
            if plm_backup_document_id.documentid:
                currentname = plm_backup_document_id.documentid.store_fname
                if plm_backup_document_id.existingfile != currentname:
                    fullname = os.path.join(
                        documentType._get_filestore(),
                        plm_backup_document_id.existingfile,
                    )
                    if os.path.exists(fullname):
                        os.chmod(fullname, stat.S_IWRITE)
                        os.unlink(fullname)
                    else:
                        logging.warning(
                            "unlink : Unable to remove the document ("
                            + str(plm_backup_document_id.documentid.name)
                            + "-"
                            + str(plm_backup_document_id.documentid.revisionid)
                            + ") from backup set. You can't change writable flag."
                        )
                        raise UserError(
                            _(
                                "Unable to remove the document ("
                                + str(plm_backup_document_id.documentid.name)
                                + "-"
                                + str(plm_backup_document_id.documentid.revisionid)
                                + ") from backup set.\n It isn't a backup file, it's original current one."
                            )
                        )
                else:
                    logging.warning(
                        "Prevent to delete the active File %r" % currentname
                    )
                    continue
            super(PlmBackupDocument, plm_backup_document_id).unlink()

    @api.model
    def getLastBckDocumentByUser(self, doc_id):
        for obj in self.search(
            [
                ("documentid", "=", doc_id.id),
                ("create_uid", "=", self.env.user.id),
            ],
            order="create_date DESC",
            limit=1,
        ):
            return obj
        return self

    @api.model
    def getLastBckDocument(self, doc_id):
        for obj in self.search(
            [
                ("documentid", "=", doc_id.id),
            ],
            order="create_date DESC",
            limit=1,
        ):
            return obj
        return self


class BackupDocWizard(models.TransientModel):
    """
    This class is called from an action in xml located in plm.backupdoc.
    Pay attention! You can restore also confirmed, released and obsoleted documents!!!
    """

    _name = "plm.backupdoc_wizard"
    _description = "Back up document wizard"

    backup_date = fields.Date(string="Backup Date", default=fields.Date.today)

    def action_restore_document(self):
        ctx = self.env.context.copy()
        ctx["check"] = False
        documentId = False
        plm_backupdoc_ids = self.env.context.get("active_ids", [])
        plm_backupdoc = self.env["plm.backupdoc"]
        ir_attachment = self.env["ir.attachment"]
        if len(plm_backupdoc_ids) > 1:
            raise UserError(
                _("Restore Document Error"),
                _("You can restore only a document at a time."),
            )
        for plm_backupdoc_id in plm_backupdoc.browse(plm_backupdoc_ids):
            ir_attachment_bck_id = plm_backupdoc_id.documentid
            if not ir_attachment_bck_id.ischecked_in():
                raise UserError(
                    """Unable to restore check-out document !!.\nMake check-in with user [ %s ]"""
                    % (ir_attachment_bck_id.checkout_user)
                )
            values = {
                "printout": plm_backupdoc_id.printout,
                "preview": plm_backupdoc_id.preview,
            }
            if ir_attachment_bck_id:
                documentId = ir_attachment_bck_id.id
                write_res = ir_attachment_bck_id.sudo().with_context(ctx).write(values)
                sql = """
                UPDATE IR_ATTACHMENT SET store_fname = %s where id = %s
                """
                self.env.cr.execute(sql, (plm_backupdoc_id.existingfile,
                                          ir_attachment_bck_id.id,
                                          ))
                if write_res:
                    logging.info(
                        "[action_restore_document] Updated document %r" % (documentId)
                    )
                else:
                    logging.warning(
                        "[action_restore_document] Updated document failed for %r"
                        % (documentId)
                    )
            else:
                # Note that if I don't have a document I can't relate it to it's component
                # User have to do it hand made
                values.update(
                    {
                        "engineering_state": "draft",
                        "engineering_revision": plm_backupdoc_id.engineering_revision,
                        "name": plm_backupdoc_id.document_name,
                    }
                )
                documentId = ir_attachment.sudo().create(values)
                if documentId:
                    logging.info(
                        "[action_restore_document] Created document %r" % (documentId)
                    )
                else:
                    logging.warning(
                        "[action_restore_document] Create document failed for %r"
                        % (documentId)
                    )

        action_vals = self.env["ir.actions.act_window"]._for_xml_id(
            "plm.plm_action_document_form"
        )
        domain = safe_eval(action_vals.get("domain", "[]"))
        domain = Domain.AND([domain, [("id", "in", [documentId])]])
        action_vals["domain"] = domain
        return action_vals

    def action_restore_all_documents(self):
        """
        Restore a document and its child documents to a selected backup date.
        Runs via a wizard and only if all documents are in draft and checked in.
        Restores both the selected document and all related children.
        """
        self.ensure_one()

        if not self.backup_date:
            raise ValidationError(_("Please select a restore date before continuing."))

        active_ids = self.env.context.get("active_ids", [])
        if len(active_ids) != 1:
            raise ValidationError(_("Please select exactly one backup document to restore."))

        root_bck = self.env["plm.backupdoc"].browse(active_ids[0])
        root_attachment = root_bck.documentid
        if not root_attachment:
            raise ValidationError(
                _("The selected backup entry has no linked document. Cannot restore.")
            )

        ir_att = self.env["ir.attachment"]
        root_id = root_attachment.id

        tree_ids = set()
        tree_ids.add(root_id)
        tree_ids.update(ir_att.getRelatedHiTree(root_id, recursion=True, getRftree=True))
        tree_ids.update(ir_att.getRelatedLyTree(root_id))
        tree_ids.update(ir_att.getRelatedRfTree(root_id, recursion=True))
        tree_ids.update(ir_att.getRelatedPkgTree(root_id))

        logging.info(
            "[action_restore_all_documents] Root id=%s → tree contains %d document(s).",
            root_id, len(tree_ids),
        )

        target_date = self.backup_date
        day_start = datetime.datetime.combine(target_date, datetime.time.min)
        day_end = datetime.datetime.combine(target_date, datetime.time.max)

        invalid_state_found = False
        not_checked_in_found = False
        backup_missing = False
        ready_pairs = []

        for att in self.env["ir.attachment"].browse(list(tree_ids)):
            if att.engineering_state != "draft":
                invalid_state_found = True
                continue

            if not att.ischecked_in():
                not_checked_in_found = True
                continue

            bck = self.env["plm.backupdoc"].search(
                [
                    ("documentid", "=", att.id),
                    ("create_date", ">=", day_start),
                    ("create_date", "<=", day_end),
                ],
                order="create_date DESC",
                limit=1,
            )

            if not bck:
                backup_missing = True
                continue

            ready_pairs.append((att, bck))
        if invalid_state_found:
            raise ValidationError(
                _("Restore is only allowed when all documents are in 'draft' state.")
            )

        if not_checked_in_found:
            raise ValidationError(
                _("All documents must be checked-in before restore.")
            )

        if backup_missing:
            raise ValidationError(
                _("The document is not available for backup on the selected date.")
            )

        ctx = self.env.context.copy()
        ctx["backup"] = False
        ctx["check"] = False

        restored_ids = []
        for att, bck in ready_pairs:
            write_res = att.sudo().with_context(ctx).write(
                {
                    "printout": bck.printout,
                    "preview": bck.preview,
                }
            )

            # Swap store_fname directly in the DB – same raw-SQL as action_restore_document
            self.env.cr.execute(
                "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
                (bck.existingfile, att.id),
            )

            if write_res:
                logging.info(
                    "[action_restore_all_documents] Restored id=%s (%s Rev.%s) "
                    "<- backup id=%s created on %s",
                    att.id, att.engineering_code, att.engineering_revision,
                    bck.id, bck.create_date,
                )
            else:
                logging.warning(
                    "[action_restore_all_documents] ORM write failed for id=%s", att.id
                )

            restored_ids.append(att.id)

        if not restored_ids:
            raise ValidationError(_("No documents were restored. Please check the server logs."))

        logging.info(
            "[action_restore_all_documents] Done – restored %d document(s): %s",
            len(restored_ids), restored_ids,
        )

        action_vals = self.env["ir.actions.act_window"]._for_xml_id(
            "plm.plm_action_document_form"
        )
        action_vals["domain"] = [("id", "in", restored_ids)]
        action_vals["name"] = _("Restored Documents")
        return action_vals
