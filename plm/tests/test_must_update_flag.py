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
from datetime import datetime, timedelta

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_must_update_flag
#
SAVE_START = datetime(2026, 10, 16, 7, 0, 0)


@tagged("-standard", "odoo_plm", "odoo_plm_must_update_flag")
class PlmMustUpdateFlag(TransactionCase, PlmEntityCreator):

    def _cad_save(self, document, db_thread, minute):
        """A CAD save of the document at SAVE_START + minute."""
        cad_open = self.env["plm.cad.open"].create(
            {
                "document_id": document.id,
                "operation_type": "save",
                "dbThread": db_thread,
            }
        )
        # the ORM stamps every record of the transaction with the same date
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE plm_cad_open SET create_date = %s, write_date = %s WHERE id = %s",
            (
                SAVE_START + timedelta(minutes=minute),
                SAVE_START + timedelta(minutes=minute),
                cad_open.id,
            ),
        )
        self.env.invalidate_all()
        return cad_open

    def _button_relations(self, document):
        action = document.related_not_update()
        return self.env["ir.attachment.relation"].search(action["domain"])

    def test_3d_rf_child_saved_later_then_parent_saved(self):
        parent = self.create_document("rf_parent.iam", doc_type="3d")
        child = self.create_document("rf_child.iam", doc_type="3d")
        self.create_link_document(parent, child, "RfTree")
        relation = self.env["ir.attachment.relation"].search(
            [("parent_id", "=", parent.id), ("link_kind", "=", "RfTree")]
        )
        #
        self._cad_save(parent, "000001", 0)
        self._cad_save(child, "000002", 10)
        parent.assign_must_update_flag()
        self.assertTrue(parent.must_update_from_cad)
        self.assertEqual(self._button_relations(parent), relation)
        #
        self._cad_save(parent, "000003", 20)
        parent.assign_must_update_flag()
        self.assertFalse(parent.must_update_from_cad)
        self.assertFalse(self._button_relations(parent))

    def test_3d_rf_child_saved_in_the_same_thread(self):
        parent = self.create_document("rf_parent_same.iam", doc_type="3d")
        child = self.create_document("rf_child_same.iam", doc_type="3d")
        self.create_link_document(parent, child, "RfTree")
        #
        self._cad_save(parent, "000010", 0)
        self._cad_save(child, "000010", 10)
        parent.assign_must_update_flag()
        self.assertFalse(parent.must_update_from_cad)
        self.assertFalse(self._button_relations(parent))

    def test_3d_flag_without_rf_children_is_cleared(self):
        parent = self.create_document("no_rf_parent.iam", doc_type="3d")
        parent.must_update_from_cad = True
        self._cad_save(parent, "000020", 0)
        parent.assign_must_update_flag()
        self.assertFalse(parent.must_update_from_cad)

    def test_2d_layout_older_than_its_model_keeps_the_flag(self):
        layout = self.create_document("layout.idw", doc_type="2d")
        model = self.create_document("model.iam", doc_type="3d")
        self.create_link_document(layout, model, "LyTree")
        relation = self.env["ir.attachment.relation"].search(
            [("parent_id", "=", layout.id), ("link_kind", "=", "LyTree")]
        )
        #
        self._cad_save(layout, "000030", 0)
        self._cad_save(model, "000031", 10)
        layout.assign_must_update_flag()
        self.assertTrue(layout.must_update_from_cad)
        self.assertEqual(self._button_relations(layout), relation)
