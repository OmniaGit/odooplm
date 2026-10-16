##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
import base64
import io
import json
import zipfile

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.plm.wizard.plm_glb_structure_import import read_custom_mapping

#
# --test-tags=odoo_plm_glb_import
#

# A CustomProcedure as the CAD client gets it: Python 2, a base class, a CAD
# class inheriting it, a dictionary that is no literal
CUSTOM_PROCEDURE = '''# -*- coding: utf-8 -*-
import logging
clerckHook_some_option = True

def hook_something(self):
    print "python 2 print"
    try:
        pass
    except Exception, ex:
        logging.error(ex)

class BaseAttributes(object):
    def __init__(self):
        self.DOCUMENT_CONVERTION = {'engineering_code': 'd_engineering_code',
                                    'engineering_revision': 'd_engineering_revision',
                                    'description': 'DOCDESC'}
        self.DOCUMENT_TYPES = {'engineering_code': 'char', 'engineering_revision': 'int'}
        self.COMPONENT_CONVERTION = {'engineering_code': 'c_engineering_code',
                                     'name': 'c_name'}
        self.COMPONENT_TYPES = {'engineering_code': 'char', 'name': 'char'}

class SolidWorksIntegrationSetting(BaseAttributes):
    def __init__(self):
        BaseAttributes.__init__(self)
        self.COMPONENT_CONVERTION = {'name': 'COMPDESC', 'engineering_material': 'COMPMAT'}
        self.RELATION_CONVERTION = {BaseDbIntegration.qty: 'RELQTY'}

class InventorIntegrationSetting(BaseAttributes):
    pass

def integrationSettings():
    integrations = {}
    integrations["solidworks"] = SolidWorksIntegrationSetting
    integrations["inventor"] = InventorIntegrationSetting
    return integrations
'''


def _entry(kind, file_name, code, revision, properties=None, configuration="", children=None):
    entry = {"kind": kind, "file": "c:/p/%s" % file_name, "file_name": file_name,
             "configuration": configuration, "engineering_code": code,
             "engineering_revision": revision, "properties": properties or {}, "warnings": []}
    if children is not None:
        entry["children"] = children
    return entry


def _child(glb, kind, file_name, quantity):
    return {"glb": glb, "kind": kind, "file": "c:/p/%s" % file_name, "file_name": file_name,
            "configuration": "", "quantity": quantity, "occurrences": []}


def _structure(cad="solidworks"):
    """top.asm (A-1) = 2 x B-1 + 1 x B-1 'Long' + 1 x sub.asm (S-1);
    sub.asm = 3 x B-1; B-1 is one part in two configurations, two .glb."""
    part_props = {"Custom": {"COMPDESC": "Bracket", "COMPMAT": "Steel"}}
    return {
        "schema": "omnia.gltf.structure", "version": 1, "exporter": "omnia_threejs_export test",
        "cad": cad, "root": "A-1_0.glb",
        "documents": {
            "A-1_0.glb": _entry("assembly", "top.asm", "A-1", 0, children=[
                _child("B-1_2.glb", "part", "b.par", 2),
                _child("B-1_2_Long.glb", "part", "b.par", 1),
                _child("S-1_0.glb", "assembly", "sub.asm", 1),
                _child(None, "part", "lost.par", 1)]),
            "B-1_2.glb": _entry("part", "b.par", "B-1", 2, part_props),
            "B-1_2_Long.glb": _entry("part", "b.par", "B-1", 2, part_props, configuration="Long"),
            "S-1_0.glb": _entry("assembly", "sub.asm", "S-1", 0, children=[
                _child("B-1_2.glb", "part", "b.par", 3)]),
        },
    }


def _zip(structure, skip=()):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in structure["documents"]:
            if name not in skip:
                archive.writestr(name, b"glTF" + name.encode())
        archive.writestr("structure.json", json.dumps(structure))
    return base64.b64encode(buffer.getvalue()).decode()


@tagged("-standard", "odoo_plm_glb_import")
class TestReadCustomMapping(TransactionCase):
    """The CustomProcedure is read, never run: Python 2 code is fine."""

    def test_cad_class_with_base(self):
        mapping, warnings = read_custom_mapping(CUSTOM_PROCEDURE, "solidworks")
        # the CAD class overrides the whole dictionary, as the client does
        self.assertEqual(mapping["COMPONENT_CONVERTION"], {"name": "COMPDESC", "engineering_material": "COMPMAT"})
        # inherited from its base
        self.assertEqual(mapping["DOCUMENT_CONVERTION"]["description"], "DOCDESC")
        # not a literal: skipped, with a warning
        self.assertNotIn("RELATION_CONVERTION", mapping)
        self.assertTrue(any("RELATION_CONVERTION" in str(w) for w in warnings))

    def test_other_cad_and_missing_cad(self):
        mapping, _warnings = read_custom_mapping(CUSTOM_PROCEDURE, "Inventor")
        self.assertEqual(mapping["COMPONENT_CONVERTION"]["name"], "c_name")
        mapping, warnings = read_custom_mapping(CUSTOM_PROCEDURE, "solidedge")
        self.assertEqual(mapping, {})
        self.assertTrue(warnings)

    def test_return_dict_style(self):
        source = ("class Sw(object):\n    COMPONENT_CONVERTION = {'name': 'X'}\n\n"
                  "def integrationSettings():\n    return {'solidworks': Sw}\n")
        mapping, _warnings = read_custom_mapping(source, "solidworks")
        self.assertEqual(mapping["COMPONENT_CONVERTION"], {"name": "X"})


@tagged("-standard", "odoo_plm_glb_import")
class TestGlbStructureImport(TransactionCase):

    def _import(self, structure, skip=()):
        wizard = self.env["plm.glb.structure.import"].create(
            {"zip_file": _zip(structure, skip), "zip_name": "top.zip"})
        wizard.action_import()
        return wizard

    def _doc(self, code, revision=0):
        return self.env["ir.attachment"].search([("engineering_code", "=", code),
                                                 ("engineering_revision", "=", revision)])

    def _product(self, code, revision=0):
        return self.env["product.product"].search([("engineering_code", "=", code),
                                                   ("engineering_revision", "=", revision)])

    def _web3d(self, native):
        return self.env["ir.attachment.relation"].search(
            [("parent_id", "=", native.id), ("link_kind", "=", "Web3DTree")]).child_id

    def test_structure(self):
        wizard = self._import(_structure())
        self.assertEqual(wizard.state, "done")
        top, part, sub = self._doc("A-1"), self._doc("B-1", 2), self._doc("S-1")
        # native documents named after the CAD file, empty, checked out to me
        self.assertEqual((top.name, part.name, sub.name), ("top.asm", "b.par", "sub.asm"))
        for native in top | part | sub:
            self.assertTrue(native.is_plm)
            self.assertTrue(self.env["plm.checkout"].search(
                [("documentid", "=", native.id), ("userid", "=", self.env.uid)]))
        # each .glb under its native document, the part with its two configurations
        self.assertEqual(sorted(self._web3d(part).mapped("name")), ["B-1_2.glb", "B-1_2_Long.glb"])
        self.assertEqual(self._web3d(top).name, "A-1_0.glb")
        self.assertEqual(self._web3d(top).raw.content, b"glTFA-1_0.glb")
        # components linked to their documents
        product_part = self._product("B-1", 2)
        self.assertIn(part, product_part.linkeddocuments)
        self.assertIn(self._web3d(part)[0], product_part.linkeddocuments)
        # BoMs: one line per child of the json, with its quantity
        top_bom = self.env["mrp.bom"].search([("product_tmpl_id", "=", self._product("A-1").product_tmpl_id.id)])
        lines = sorted((line.product_id.engineering_code, line.product_qty) for line in top_bom.bom_line_ids)
        self.assertEqual(lines, [("B-1", 1.0), ("B-1", 2.0), ("S-1", 1.0)])
        sub_bom = self.env["mrp.bom"].search([("product_tmpl_id", "=", self._product("S-1").product_tmpl_id.id)])
        self.assertEqual([(line.product_id.engineering_code, line.product_qty) for line in sub_bom.bom_line_ids],
                         [("B-1", 3.0)])
        # HiTree between the native documents
        hitree = self.env["ir.attachment.relation"].search([("parent_id", "=", top.id), ("link_kind", "=", "HiTree")])
        self.assertEqual(set(hitree.child_id.ids), {part.id, sub.id})
        # the child with no file is reported, not imported
        self.assertIn("lost.par", wizard.result)
        if "has_web3d" in top._fields:
            self.assertTrue(top.has_web3d)

    def test_reimport_is_idempotent(self):
        self._import(_structure())
        self._import(_structure())
        self.assertEqual(len(self._doc("B-1", 2)), 1)
        self.assertEqual(len(self._web3d(self._doc("B-1", 2))), 2)
        top_bom = self.env["mrp.bom"].search([("product_tmpl_id", "=", self._product("A-1").product_tmpl_id.id)])
        self.assertEqual(len(top_bom.bom_line_ids), 3)

    def test_file_name_required(self):
        structure = _structure()
        structure["documents"]["B-1_2.glb"]["file_name"] = None
        with self.assertRaises(UserError):
            self._import(structure)

    def test_glb_missing_from_zip(self):
        with self.assertRaises(UserError):
            self._import(_structure(), skip=("S-1_0.glb",))

    def test_existing_native_document_is_reused(self):
        native = self.env["ir.attachment"].create({"name": "b.par", "engineering_code": "B-1",
                                                   "engineering_revision": 2, "is_plm": True,
                                                   "raw": b"native cad file"})
        self._import(_structure())
        self.assertEqual(self._doc("B-1", 2), native)
        self.assertEqual(native.raw.content, b"native cad file")
        self.assertFalse(self.env["plm.checkout"].search([("documentid", "=", native.id)]))
        self.assertEqual(len(self._web3d(native)), 2)

    def test_released_component_keeps_its_bom(self):
        self._import(_structure())
        product_top = self._product("A-1")
        bom = self.env["mrp.bom"].search([("product_tmpl_id", "=", product_top.product_tmpl_id.id)])
        before = sorted(bom.bom_line_ids.ids)
        product_top.engineering_state = "released"
        structure = _structure()
        structure["documents"]["A-1_0.glb"]["children"] = structure["documents"]["A-1_0.glb"]["children"][:1]
        wizard = self._import(structure)
        self.assertEqual(sorted(bom.bom_line_ids.ids), before)
        self.assertIn("released", wizard.result)

    def test_custom_procedure_of_the_group(self):
        if "custom_procedure" not in self.env["res.users"]._fields:
            self.skipTest("plm_client_customprocedure is not installed")
        group = self.env["res.groups"].create({"name": "GLB import mapping",
                                               "custom_procedure": base64.b64encode(CUSTOM_PROCEDURE.encode()).decode()})
        self.env.user.group_ids = [(4, group.id)]
        self.env.user.custom_procedure = False
        wizard = self._import(_structure())
        self.assertEqual(self._product("B-1", 2).name, "Bracket")
        self.assertIn("CustomProcedure", wizard.result)
