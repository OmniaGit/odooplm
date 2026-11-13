##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
import importlib.util
import io
import os
import uuid

from PIL import Image

from odoo.modules.module import get_module_path
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.binary import BinaryBytes

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_preview_filestore
#


def _png(color):
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(buf, "PNG")
    return buf.getvalue()


def _load_migration():
    path = os.path.join(
        get_module_path("plm"), "upgrades", "20.0.1.0.41", "post-migrate.py"
    )
    spec = importlib.util.spec_from_file_location("plm_preview_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-standard", "odoo_plm", "odoo_plm_preview_filestore")
class PlmPreviewFilestore(TransactionCase, PlmEntityCreator):

    def _doc(self, prefix="prev"):
        return self.create_document("%s_%s.prt" % (prefix, uuid.uuid4().hex))

    def _stored(self, model, field, res_id):
        return self.env["ir.attachment"].sudo().search([
            ("res_model", "=", model),
            ("res_field", "=", field),
            ("res_id", "=", res_id),
        ])

    def _column_exists(self, table, column):
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.columns"
            " WHERE table_schema = current_schema()"
            " AND table_name = %s AND column_name = %s",
            (table, column),
        )
        return bool(self.env.cr.rowcount)

    def test_preview_stored_in_filestore(self):
        doc = self._doc()
        png = _png("red")
        doc.preview = BinaryBytes(png)
        self.env.flush_all()
        stored = self._stored("ir.attachment", "preview", doc.id)
        self.assertEqual(len(stored), 1)
        self.assertTrue(stored.store_fname, "the preview is a file of the filestore")
        doc.invalidate_recordset(["preview"])
        self.assertEqual(bytes(doc.preview), png)

    def test_preview_related_shares_the_parent_file(self):
        parent = self._doc("parent")
        child = self._doc("child")
        parent.preview = BinaryBytes(_png("blue"))
        relation = self.env["ir.attachment.relation"].create({
            "parent_id": parent.id,
            "child_id": child.id,
            "link_kind": "ExtraTree",
        })
        self.env.flush_all()
        parent_file = self._stored("ir.attachment", "preview", parent.id)
        related_file = self._stored(
            "ir.attachment.relation", "preview_related", relation.id
        )
        self.assertEqual(len(related_file), 1)
        self.assertEqual(
            related_file.store_fname, parent_file.store_fname,
            "an identical image takes one file only",
        )

    def test_unlink_removes_the_preview(self):
        doc = self._doc()
        doc.preview = BinaryBytes(_png("green"))
        self.env.flush_all()
        stored = self._stored("ir.attachment", "preview", doc.id)
        doc.unlink()
        self.assertFalse(stored.exists())

    def test_migration_moves_the_column(self):
        """The script moves the bytea column into the filestore, released
        documents included, and drops the column."""
        cr = self.env.cr
        if not self._column_exists("ir_attachment", "preview"):
            cr.execute("ALTER TABLE ir_attachment ADD COLUMN preview bytea")
        draft = self._doc("mig_draft")
        released = self._doc("mig_released")
        png_draft, png_released = _png("yellow"), _png("purple")
        cr.execute(
            "UPDATE ir_attachment SET preview = %s WHERE id = %s",
            (png_draft, draft.id),
        )
        cr.execute(
            "UPDATE ir_attachment SET preview = %s, engineering_state = 'released'"
            " WHERE id = %s",
            (png_released, released.id),
        )
        self.env.invalidate_all()
        migration = _load_migration()
        moved = migration.move_column_to_filestore(
            self.env, "ir_attachment", "ir.attachment", "preview"
        )
        self.assertGreaterEqual(moved, 2)
        self.assertFalse(self._column_exists("ir_attachment", "preview"))
        self.env.invalidate_all()
        self.assertEqual(bytes(draft.preview), png_draft)
        self.assertEqual(bytes(released.preview), png_released)
        self.assertEqual(released.engineering_state, "released")
        # Run again, there is nothing left to move.
        self.assertEqual(
            migration.move_column_to_filestore(
                self.env, "ir_attachment", "ir.attachment", "preview"
            ),
            0,
        )

    def test_migration_skips_values_already_moved(self):
        """A record whose preview is already in the filestore keeps it."""
        cr = self.env.cr
        if not self._column_exists("ir_attachment", "preview"):
            cr.execute("ALTER TABLE ir_attachment ADD COLUMN preview bytea")
        doc = self._doc("mig_twice")
        png_new = _png("black")
        doc.preview = BinaryBytes(png_new)
        self.env.flush_all()
        cr.execute(
            "UPDATE ir_attachment SET preview = %s WHERE id = %s",
            (_png("white"), doc.id),
        )
        _load_migration().move_column_to_filestore(
            self.env, "ir_attachment", "ir.attachment", "preview"
        )
        self.env.invalidate_all()
        self.assertEqual(len(self._stored("ir.attachment", "preview", doc.id)), 1)
        self.assertEqual(bytes(doc.preview), png_new)

    def test_search_on_the_binary_fields(self):
        """(field, '!=', False) finds the documents whose file is set, and
        (field, '=', False) the others, for every binary field of
        ir.attachment in the filestore."""
        Attachment = self.env["ir.attachment"]
        with_value = self._doc("search_set")
        without_value = self._doc("search_unset")
        with_value.write({
            "preview": BinaryBytes(_png("orange")),
            "preview_related": BinaryBytes(_png("gray")),
            "printout": BinaryBytes(b"%PDF-1.4 printout"),
        })
        self.env.flush_all()
        ids = [with_value.id, without_value.id]
        for field in ("preview", "preview_related", "printout"):
            self.assertEqual(
                Attachment.search([("id", "in", ids), (field, "!=", False)]),
                with_value, field,
            )
            self.assertEqual(
                Attachment.search([("id", "in", ids), (field, "=", False)]),
                without_value, field,
            )

    def test_search_on_the_relation_preview(self):
        parent = self._doc("rel_parent")
        child = self._doc("rel_child")
        parent.preview = BinaryBytes(_png("navy"))
        Relation = self.env["ir.attachment.relation"]
        with_value = Relation.create({
            "parent_id": parent.id, "child_id": child.id, "link_kind": "ExtraTree",
        })
        without_value = Relation.create({
            "parent_id": child.id, "child_id": parent.id, "link_kind": "HiTree",
        })
        self.env.flush_all()
        ids = [with_value.id, without_value.id]
        self.assertEqual(
            Relation.search([("id", "in", ids), ("preview_related", "!=", False)]),
            with_value,
        )
