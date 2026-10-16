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

from PIL import Image

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.plm.wizard.plm_glb_structure_import import mapping_for_cad, read_web_mapping

#
# --test-tags=odoo_plm_glb_import
#

# A CustomProcedure holding WEB_GLB_IMPORT among other code, Python 2 that a
# Python 3 server could not import: only the dictionary is read
CUSTOM_PROCEDURE = '''# -*- coding: utf-8 -*-
SOME_OPTION = True

def some_function(self):
    print "python 2"

WEB_GLB_IMPORT = {
    "*": {"product": {"name": "Label", "engineering_material": "Stuff"},
          "document": {"description": "Title"}},
    "solidworks": {"product": {"name": "Long label", "engineering_surface": "Finish"}},
    "inventor": {"product": {"engineering_surface": "Coat"}},
}
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
    part_props = {"Custom": {"Label": "Bracket", "Long label": "Bracket plate", "Stuff": "Steel",
                             "Finish": "Painted", "Title": "The bracket"}}
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


def _png(color):
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buffer, "PNG")
    return buffer.getvalue()


def _colour(image_value):
    """The colour of a preview, as Odoo stores it."""
    return Image.open(io.BytesIO(image_value.content)).convert("RGB").getpixel((0, 0))


def _with_previews(structure):
    """Each document names its preview, <its .glb's name>.png, as the
    converter writes it."""
    for name, entry in structure["documents"].items():
        entry["preview"] = name[:-4] + ".png"
    return structure


PREVIEW_COLOURS = {"A-1_0.png": (255, 0, 0), "B-1_2.png": (0, 255, 0),
                   "B-1_2_Long.png": (0, 255, 0), "S-1_0.png": (0, 0, 255)}


def _zip(structure, skip=()):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, entry in structure["documents"].items():
            if name not in skip:
                archive.writestr(name, b"glTF" + name.encode())
            png = entry.get("preview")
            if png and png not in skip:
                archive.writestr(png, _png(PREVIEW_COLOURS.get(png, (9, 9, 9))))
        archive.writestr("structure.json", json.dumps(structure))
    return base64.b64encode(buffer.getvalue()).decode()


@tagged("-standard", "odoo_plm_glb_import")
class TestReadWebMapping(TransactionCase):
    """WEB_GLB_IMPORT is read as text, never run."""

    def test_star_and_cad(self):
        mapping = read_web_mapping(CUSTOM_PROCEDURE)
        solidworks = mapping_for_cad(mapping, "SolidWorks")
        # the CAD's entries are added to "*" field by field
        self.assertEqual(solidworks["product"], {"name": "Long label", "engineering_material": "Stuff",
                                                 "engineering_surface": "Finish"})
        self.assertEqual(solidworks["document"], {"description": "Title"})
        # a CAD with no entry of its own takes "*"
        self.assertEqual(mapping_for_cad(mapping, "solidedge")["product"],
                         {"name": "Label", "engineering_material": "Stuff"})

    def test_absent_and_invalid(self):
        self.assertIsNone(read_web_mapping("OTHER = {}\n"))
        for bad in ("WEB_GLB_IMPORT = {'*': {'product': {'name': some_variable}}}\n",
                    "WEB_GLB_IMPORT = {'*': {'bom': {'name': 'X'}}}\n",
                    "WEB_GLB_IMPORT = {'*': {'product': {'name': 3}}}\n",
                    "WEB_GLB_IMPORT = {'*': {'product': {'name': 'X'}}\n"):
            with self.assertRaises(ValueError):
                read_web_mapping(bad)


@tagged("-standard", "odoo_plm_glb_import")
class TestGlbStructureImport(TransactionCase):

    def _import(self, structure, skip=(), **options):
        wizard = self.env["plm.glb.structure.import"].create(
            dict({"zip_file": _zip(structure, skip), "zip_name": "top.zip"}, **options))
        wizard.action_import()
        return wizard

    def _doc(self, code, revision=0):
        return self.env["ir.attachment"].search([("engineering_code", "=", code),
                                                 ("engineering_revision", "=", revision)])

    def _glb(self, name):
        return self._doc(name, 0)

    def _product(self, code, revision=0):
        return self.env["product.product"].search([("engineering_code", "=", code),
                                                   ("engineering_revision", "=", revision)])

    def _children(self, parent, kind):
        return self.env["ir.attachment.relation"].search(
            [("parent_id", "=", parent.id), ("link_kind", "=", kind)]).child_id

    def _bom(self, code):
        return self.env["mrp.bom"].search([("product_tmpl_id", "=", self._product(code).product_tmpl_id.id)])

    def _lines(self, code):
        return sorted((line.product_id.engineering_code, line.product_qty, line.source_id.name or False)
                      for line in self._bom(code).bom_line_ids)

    def _native(self, name, code, revision=0, **values):
        return self.env["ir.attachment"].create(dict(
            {"name": name, "engineering_code": code, "engineering_revision": revision, "is_plm": True}, **values))

    def test_structure_without_natives(self):
        wizard = self._import(_structure())
        self.assertEqual(wizard.state, "done")
        # no native document is created: a CAD file name must hold that file
        self.assertFalse(self.env["ir.attachment"].search([("name", "in", ["top.asm", "b.par", "sub.asm"])]))
        top, part, part_long, sub = (self._glb(name) for name in
                                     ("A-1_0.glb", "B-1_2.glb", "B-1_2_Long.glb", "S-1_0.glb"))
        self.assertTrue(all((top, part, part_long, sub)))
        self.assertEqual(top.raw.content, b"glTFA-1_0.glb")
        self.assertFalse(self.env["plm.checkout"].search([("documentid", "in", (top | part | sub).ids)]))
        # the .glb linked to its component, both configurations to the one product
        self.assertEqual(self._product("B-1", 2).linkeddocuments, part | part_long)
        # WebHiTree between the .glb files, no HiTree
        self.assertEqual(self._children(top, "WebHiTree"), part | part_long | sub)
        self.assertEqual(self._children(sub, "WebHiTree"), part)
        self.assertFalse(self._children(top, "HiTree"))
        # the BoM lines with the assembly's .glb as source
        self.assertEqual(self._lines("A-1"), [("B-1", 1.0, "A-1_0.glb"), ("B-1", 2.0, "A-1_0.glb"),
                                              ("S-1", 1.0, "A-1_0.glb")])
        self.assertEqual(self._lines("S-1"), [("B-1", 3.0, "S-1_0.glb")])
        self.assertIn("lost.par", wizard.result)

    def test_reimport_with_references_updates(self):
        self._import(_structure())
        lines_before = self._bom("A-1").bom_line_ids
        structure = _structure()
        top = structure["documents"]["A-1_0.glb"]
        top["children"] = [child for child in top["children"] if child["glb"] != "S-1_0.glb"]
        top["children"][0]["quantity"] = 5
        self._import(structure)
        self.assertEqual(len(self._glb("B-1_2.glb")), 1)
        # the WebHiTree follows the json: the subassembly is gone
        self.assertEqual(self._children(self._glb("A-1_0.glb"), "WebHiTree"),
                         self._glb("B-1_2.glb") | self._glb("B-1_2_Long.glb"))
        self.assertEqual(self._lines("A-1"), [("B-1", 1.0, "A-1_0.glb"), ("B-1", 5.0, "A-1_0.glb")])
        # the lines are the same records, updated
        self.assertLessEqual(self._bom("A-1").bom_line_ids, lines_before)

    def test_bom_without_references(self):
        self._import(_structure(), bom_mode="none")
        self.assertEqual(self._lines("A-1"), [("B-1", 1.0, False), ("B-1", 2.0, False), ("S-1", 1.0, False)])
        # a new import cannot tell the lines apart: the assembly is left out
        wizard = self._import(_structure(), bom_mode="none")
        self.assertEqual(len(self._bom("A-1").bom_line_ids), 3)
        self.assertIn("delete it before re-importing", wizard.result)

    def test_file_name_required(self):
        structure = _structure()
        structure["documents"]["B-1_2.glb"]["file_name"] = None
        with self.assertRaises(UserError):
            self._import(structure)

    def test_glb_missing_from_zip(self):
        with self.assertRaises(UserError):
            self._import(_structure(), skip=("S-1_0.glb",))

    def test_existing_native_document(self):
        native = self._native("b.par", "B-1", 2, raw=b"native cad file")
        self._import(_structure())
        self.assertEqual(native.raw.content, b"native cad file")
        self.assertEqual(self._children(native, "Web3DTree"), self._glb("B-1_2.glb") | self._glb("B-1_2_Long.glb"))
        self.assertIn(native, self._product("B-1", 2).linkeddocuments)
        self.assertFalse(self.env["plm.checkout"].search([("documentid", "=", native.id)]))
        if "has_web3d" in native._fields:
            self.assertTrue(native.has_web3d)

    def test_released_component_keeps_its_bom(self):
        self._import(_structure())
        bom = self._bom("A-1")
        before = sorted(bom.bom_line_ids.ids)
        self._product("A-1").engineering_state = "released"
        structure = _structure()
        structure["documents"]["A-1_0.glb"]["children"] = structure["documents"]["A-1_0.glb"]["children"][:1]
        wizard = self._import(structure)
        self.assertEqual(sorted(bom.bom_line_ids.ids), before)
        self.assertIn("released", wizard.result)

    def test_doc_structure_follows_the_web_tree(self):
        self._import(_structure())
        top = self._glb("A-1_0.glb")
        children = {child["id"] for child in top.getDocBom()["children"]}
        self.assertEqual(children, set(self._glb("B-1_2.glb") | self._glb("B-1_2_Long.glb") | self._glb("S-1_0.glb")))
        # a CAD document keeps its HiTree structure
        cad_top = self._native("cad_top.asm", "CAD-TOP", document_type="3d")
        cad_child = self._native("cad_child.par", "CAD-CHILD", document_type="3d")
        self.env["ir.attachment.relation"].create({"parent_id": cad_top.id, "child_id": cad_child.id,
                                                   "link_kind": "HiTree"})
        self.assertEqual({child["id"] for child in cad_top.getDocBom()["children"]}, {cad_child})

    def _clear_procedures(self):
        if "custom_procedure" not in self.env["res.users"]._fields:
            self.skipTest("plm_client_customprocedure is not installed")
        self.env.user.custom_procedure = False
        for group in self.env.user.group_ids:
            group.custom_procedure = False

    def test_web_mapping_of_the_group(self):
        self._clear_procedures()
        group = self.env["res.groups"].create({"name": "GLB import mapping",
                                               "custom_procedure": base64.b64encode(CUSTOM_PROCEDURE.encode()).decode()})
        self.env.user.group_ids = [(4, group.id)]
        wizard = self._import(_structure())
        product = self._product("B-1", 2)
        self.assertEqual(product.name, "Bracket plate")
        self.assertEqual(product.engineering_material, "Steel")
        self.assertEqual(product.engineering_surface, "Painted")
        # the document section goes to the .glb (and to a native document, when there is one)
        self.assertEqual(self._glb("B-1_2.glb").description, "The bracket")
        self.assertIn("WEB_GLB_IMPORT", wizard.result)

    def test_field_types_and_unknown_fields(self):
        self._clear_procedures()
        procedure = ("WEB_GLB_IMPORT = {'*': {'product': {'weight': 'Mass', 'no_such_field': 'Label'}}}\n")
        self.env.user.custom_procedure = base64.b64encode(procedure.encode()).decode()
        structure = _structure()
        structure["documents"]["B-1_2.glb"]["properties"]["Custom"]["Mass"] = "1,5"
        wizard = self._import(structure)
        self.assertEqual(self._product("B-1", 2).weight, 1.5)
        self.assertIn("no_such_field", wizard.result)

    def test_no_web_mapping(self):
        self._clear_procedures()
        self.env.user.custom_procedure = base64.b64encode(b"SOMETHING = 1\n").decode()
        wizard = self._import(_structure())
        self.assertEqual(self._product("B-1", 2).name, "B-1")
        self.assertIn("has no WEB_GLB_IMPORT", wizard.result)

    def test_invalid_web_mapping_stops(self):
        self._clear_procedures()
        self.env.user.custom_procedure = base64.b64encode(b"WEB_GLB_IMPORT = {'*': {'bom': {}}}\n").decode()
        with self.assertRaises(UserError):
            self._import(_structure())

    def test_previews_and_product_images(self):
        wizard = self._import(_with_previews(_structure()))
        self.assertEqual(_colour(self._glb("A-1_0.glb").preview), (255, 0, 0))
        self.assertEqual(_colour(self._glb("S-1_0.glb").preview), (0, 0, 255))
        # a product with no image gets the preview
        self.assertEqual(_colour(self._product("A-1").image_1920), (255, 0, 0))
        self.assertEqual(_colour(self._product("B-1", 2).image_1920), (0, 255, 0))
        self.assertNotIn("preview", wizard.result)

    def test_product_image_kept_unless_forced(self):
        self._import(_structure())
        product = self._product("A-1")
        product.image_1920 = base64.b64encode(_png((1, 2, 3))).decode()
        self._import(_with_previews(_structure()))
        self.assertEqual(_colour(product.image_1920), (1, 2, 3))
        self._import(_with_previews(_structure()), force_product_images=True)
        self.assertEqual(_colour(product.image_1920), (255, 0, 0))

    def test_preview_replaces_the_native_one(self):
        native = self._native("b.par", "B-1", 2, preview=base64.b64encode(_png((1, 2, 3))).decode())
        self._import(_with_previews(_structure()))
        self.assertEqual(_colour(native.preview), (0, 255, 0))

    def test_released_native_keeps_its_preview(self):
        native = self._native("b.par", "B-1", 2, preview=base64.b64encode(_png((1, 2, 3))).decode())
        native.engineering_state = "released"
        wizard = self._import(_with_previews(_structure()))
        self.assertEqual(_colour(native.preview), (1, 2, 3))
        self.assertEqual(_colour(self._glb("B-1_2.glb").preview), (0, 255, 0))
        self.assertEqual(wizard.result.count("its preview is left as it is"), 1)

    def test_missing_previews_are_reported(self):
        structure = _with_previews(_structure())
        structure["documents"]["S-1_0.glb"]["preview"] = None
        wizard = self._import(structure, skip=("A-1_0.png",))
        self.assertIn("S-1_0.glb: no preview in the zip", wizard.result)
        self.assertIn("A-1_0.glb: its preview A-1_0.png is not in the zip", wizard.result)
        self.assertFalse(self._glb("A-1_0.glb").preview)
        self.assertEqual(_colour(self._glb("B-1_2.glb").preview), (0, 255, 0))
