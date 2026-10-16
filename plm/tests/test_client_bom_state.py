# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""
Created on 16 Oct 2026

@author: mboscolo
"""
import json

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.plm.tests.entity_creator import PlmEntityCreator

#
# --test-tags=odoo_plm_bom_state
#


@tagged("-standard", "odoo_plm_bom_state")
class PlmClientBomState(TransactionCase, PlmEntityCreator):
    """plm.client.get_bom_state answers what saveRelationNew would do."""

    def setUp(self):
        super().setUp()
        self.parent, self.parent_doc = self.create_product_document("bs_parent")
        self.bolt, self.bolt_doc = self.create_product_document("bs_bolt")
        self.nut, self.nut_doc = self.create_product_document("bs_nut")
        self.client = self.env["plm.client"]

    def _save(self, children):
        """Save from the CAD: children are (product, document) pairs."""
        self.env["mrp.bom"].saveRelationNew([
            (self.parent_doc.id, self.parent.id, self.parent_doc.id),
            [(product.id, document.id, {"product_qty": 1}) for product, document in children],
        ])

    def _key(self, record):
        return [record.engineering_code, record.engineering_revision]

    def _ask(self, children, attributes=None):
        structure = [{
            "product": self._key(self.parent),
            "document": self._key(self.parent_doc),
            "children": [{"product": self._key(product),
                          "document": self._key(document),
                          "attributes": (attributes or {}).get(product.id, {})}
                         for product, document in children],
        }]
        return json.loads(self.client.get_bom_state(json.dumps(structure)))[0]

    def _bom(self):
        return self.env["mrp.bom"].search([("product_tmpl_id", "=", self.parent.product_tmpl_id.id)])

    def test_nothing_in_odoo_yet(self):
        state = self._ask([(self.bolt, self.bolt_doc)])
        self.assertEqual(state["product_id"], self.parent.id)
        self.assertEqual(state["document_id"], self.parent_doc.id)
        self.assertFalse(state["bom_id"])
        self.assertEqual(state["children"][0]["product_id"], self.bolt.id)
        self.assertFalse(state["children"][0]["line_id"])
        self.assertEqual(state["lines_removed"], [])
        self.assertFalse(self._bom(), "the check created a BOM")

    def test_the_same_structure_reuses_every_line(self):
        rows = [(self.bolt, self.bolt_doc), (self.bolt, self.bolt_doc), (self.nut, self.nut_doc)]
        self._save(rows)
        bom = self._bom()
        lines_before = bom.bom_line_ids.ids
        state = self._ask(rows)
        self.assertEqual(state["bom_id"], bom.id)
        self.assertEqual(state["bom_type"], bom.type)
        line_ids = [child["line_id"] for child in state["children"]]
        self.assertEqual(sorted(line_ids), sorted(lines_before))
        self.assertEqual(state["lines_removed"], [])
        self.assertFalse(state["bom_removed"])
        # and the save agrees: the same lines afterwards
        self._save(rows)
        self.assertEqual(sorted(self._bom().bom_line_ids.ids), sorted(lines_before))

    def test_a_row_dropped_or_excluded_is_a_line_removed(self):
        self._save([(self.bolt, self.bolt_doc), (self.nut, self.nut_doc)])
        nut_line = self._bom().bom_line_ids.filtered(lambda line: line.product_id == self.nut)
        dropped = self._ask([(self.bolt, self.bolt_doc)])
        self.assertEqual(dropped["lines_removed"], nut_line.ids)
        excluded = self._ask([(self.bolt, self.bolt_doc), (self.nut, self.nut_doc)],
                             attributes={self.nut.id: {"EXCLUDE": True}})
        self.assertFalse(excluded["children"][1]["line_id"])
        self.assertEqual(excluded["lines_removed"], nut_line.ids)

    def test_a_line_added_by_hand_is_left_alone(self):
        self._save([(self.bolt, self.bolt_doc)])
        bom = self._bom()
        by_hand = self.env["mrp.bom.line"].create(
            {"bom_id": bom.id, "product_id": self.nut.id, "product_qty": 1})
        state = self._ask([])
        self.assertNotIn(by_hand.id, state["lines_removed"])
        self.assertEqual(len(state["lines_removed"]), 1)
        self.assertFalse(state["bom_removed"])

    def test_dropping_every_row_removes_the_bom(self):
        self._save([(self.bolt, self.bolt_doc)])
        self.assertTrue(self._ask([])["bom_removed"])

    def test_it_writes_nothing(self):
        self._save([(self.bolt, self.bolt_doc)])
        boms = self.env["mrp.bom"].search_count([])
        lines = self.env["mrp.bom.line"].search_count([])
        self._ask([(self.nut, self.nut_doc)])
        self.assertEqual(self.env["mrp.bom"].search_count([]), boms)
        self.assertEqual(self.env["mrp.bom.line"].search_count([]), lines)

    def test_unknown_codes(self):
        structure = [{"product": ["NOPE-CODE", 0], "document": ["NOPE-DOC", ""],
                      "children": [{"product": ["NOPE-CHILD", None]}]}]
        state = json.loads(self.client.get_bom_state(json.dumps(structure)))[0]
        self.assertFalse(state["product_id"])
        self.assertFalse(state["bom_id"])
        self.assertFalse(state["children"][0]["product_id"])
        self.assertFalse(state["children"][0]["line_id"])
