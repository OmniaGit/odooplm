##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os
import uuid
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.models.plm_backup_document import KEEP_BACKUP_PARAM
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_clean_backups
#


@tagged("-standard", "odoo_plm", "odoo_plm_clean_backups")
class PlmCleanReleasedBackups(TransactionCase, PlmEntityCreator):

    def setUp(self):
        super().setUp()
        self.backup = self.env["plm.backupdoc"]
        self.filestore = self.env["ir.attachment"]._get_filestore()
        self.env["ir.config_parameter"].sudo().set_param(KEEP_BACKUP_PARAM, False)

    def _document(self, state):
        doc = self.create_document("clean_bck_%s_%s.prt" % (state, uuid.uuid4().hex))
        self.env.cr.execute(
            "UPDATE ir_attachment SET engineering_state = %s WHERE id = %s",
            (state, doc.id),
        )
        doc.invalidate_recordset(["engineering_state"])
        return doc

    def _backup(self, doc, file_name=None, write_file=True):
        if file_name is None:
            file_name = os.path.join("tbck", uuid.uuid4().hex + "OdooPLM_BCK")
        full_path = os.path.join(self.filestore, file_name)
        if write_file:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as fobj:
                fobj.write(b"backup content")
            self.addCleanup(
                lambda: os.path.exists(full_path) and os.unlink(full_path)
            )
        return self.backup.create({"documentid": doc.id, "existingfile": file_name})

    def _path(self, backup_id):
        return os.path.join(self.filestore, backup_id.existingfile)

    def _clean(self):
        while self.backup._clean_released_backups_batch(batch_size=2)[0]:
            pass
        # the files go only after the commit: run the hooks of this cursor
        self.env.cr.postcommit.run()

    def test_cron_batches(self):
        """The cron removes batch after batch, reporting each one to the
        progress API, which commits it in a real cron run."""
        doc = self._document("released")
        backup_ids = [self._backup(doc).id for _i in range(5)]
        calls = []

        def commit_progress(cron, processed=0, *, remaining=None, deactivate=False):
            calls.append((processed, remaining))
            return 10.0

        with patch.object(
            type(self.env["ir.cron"]), "_commit_progress", commit_progress
        ):
            self.backup._cron_clean_released_backups(batch_size=2)
        self.assertEqual([c[0] for c in calls], [2, 2, 1])
        self.assertEqual(calls[-1][1], 0)
        self.assertFalse(self.backup.browse(backup_ids).exists())

    def test_closed_states_cleaned(self):
        """Backups of released, obsoleted and under modify documents go, rows
        and files; the backups of draft and confirmed documents stay."""
        removed = []
        for state in ("released", "obsoleted", "undermodify"):
            doc = self._document(state)
            removed += [self._backup(doc), self._backup(doc)]
        kept = [self._backup(self._document(s)) for s in ("draft", "confirmed")]
        paths_removed = [self._path(b) for b in removed]
        paths_kept = [self._path(b) for b in kept]
        removed_ids = [b.id for b in removed]
        self._clean()
        self.assertFalse(self.backup.browse(removed_ids).exists())
        self.assertFalse([p for p in paths_removed if os.path.exists(p)])
        self.assertEqual(len(self.backup.browse([b.id for b in kept]).exists()), 2)
        self.assertTrue(all(os.path.exists(p) for p in paths_kept))

    def test_keep_setting(self):
        """With the setting on nothing is removed."""
        self.env["ir.config_parameter"].sudo().set_param(KEEP_BACKUP_PARAM, True)
        backup_id = self._backup(self._document("released"))
        self.backup._cron_clean_released_backups()
        self.env.cr.postcommit.run()
        self.assertTrue(backup_id.exists())
        self.assertTrue(os.path.exists(self._path(backup_id)))

    def test_setting_saved(self):
        """The setting saved from the settings page stops the cleaning."""
        self.env["res.config.settings"].create({"keep_released_backups": True}).execute()
        self.assertTrue(self.backup._keep_released_backups())
        self.env["res.config.settings"].create({"keep_released_backups": False}).execute()
        self.assertFalse(self.backup._keep_released_backups())

    def test_shared_file_kept(self):
        """A file still used by another backup or by an attachment stays."""
        released = self._document("released")
        draft = self._document("draft")
        shared = self._backup(released)
        self._backup(draft, file_name=shared.existingfile, write_file=False)
        restored = self._backup(released)
        restored_doc = self._document("draft")
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
            (restored.existingfile, restored_doc.id),
        )
        paths = [self._path(shared), self._path(restored)]
        self._clean()
        self.assertFalse(self.backup.search([("documentid", "=", released.id)]))
        self.assertTrue(all(os.path.exists(p) for p in paths))

    def test_same_file_as_attachment(self):
        """A backup of the released document that shares the file of the
        document itself is removed from the database only: the file stays."""
        doc = self._document("released")
        backup_id = self._backup(doc)
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
            (backup_id.existingfile, doc.id),
        )
        path = self._path(backup_id)
        backup_ref = backup_id.id
        self._clean()
        self.assertFalse(self.backup.browse(backup_ref).exists())
        self.assertTrue(os.path.exists(path))

    def test_missing_file(self):
        """A backup whose file is missing is removed without error."""
        doc = self._document("released")
        missing = self._backup(doc, write_file=False)
        present = self._backup(doc)
        path = self._path(present)
        ids = [missing.id, present.id]
        self._clean()
        self.assertFalse(self.backup.browse(ids).exists())
        self.assertFalse(os.path.exists(path))

    def test_outside_filestore(self):
        """A file name pointing outside the filestore is never deleted."""
        outside = os.path.join(os.path.dirname(self.filestore), uuid.uuid4().hex)
        with open(outside, "wb") as fobj:
            fobj.write(b"not a backup")
        self.addCleanup(lambda: os.path.exists(outside) and os.unlink(outside))
        self._backup(
            self._document("released"),
            file_name=os.path.join("..", os.path.basename(outside)),
            write_file=False,
        )
        self._clean()
        self.assertTrue(os.path.exists(outside))

    def test_cad_open_link(self):
        """The CAD open records lose the link to the removed backup, and
        checkNewer of the released document answers not newer."""
        doc = self._document("released")
        backup_id = self._backup(doc)
        cad_open = self.env["plm.cad.open"].create(
            {
                "plm_backup_doc_id": backup_id.id,
                "userid": self.env.user.id,
                "document_id": doc.id,
                "pws_path": "c:\\pws",
                "hostname": "host1",
                "operation_type": "save",
            }
        )
        self._clean()
        cad_open.invalidate_recordset()
        self.assertTrue(cad_open.exists())
        self.assertFalse(cad_open.plm_backup_doc_id)
        self.assertFalse(doc.checkNewer("host1", "c:\\pws"))
