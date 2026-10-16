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
"""Import the "All files with data" zip of OmniaGLTFConverter.

The zip holds one .glb per document and structure.json (schema
omnia.gltf.structure, written by omnia_threejs_export.cad3d_export.structure):
for every .glb its CAD file name, code, revision and property sets, and for
an assembly its direct children with their quantity. The native CAD files are
not in it.

For every document of the json the wizard finds or creates the product and
the native CAD document (empty when new, checked out to the importing user so
that the CAD client can save its file into it), uploads the .glb as a child of
the native document (Web3DTree, the relation the 3D viewer reads) and builds
the BoM and the HiTree relations of the assemblies.

The CAD properties go to Odoo fields through the client CustomProcedure of
the user or of their group, as the CAD client does: the *_CONVERTION
dictionaries of the class integrationSettings() names for the CAD. The
procedure is Python 2 code written for the client: it is read, never run on
the server; only its dictionaries written as literals are taken.
"""
import ast
import base64
import io
import json
import logging
import re
import zipfile

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.plm.models.plm_mixin import OBSOLATED_STATUS, RELEASED_STATUS

_logger = logging.getLogger(__name__)

STRUCTURE_FILE = "structure.json"
STRUCTURE_SCHEMA = "omnia.gltf.structure"
LOCKED_STATES = (RELEASED_STATUS, OBSOLATED_STATUS)
MAPPING_NAMES = (
    "DOCUMENT_CONVERTION", "DOCUMENT_TYPES",
    "COMPONENT_CONVERTION", "COMPONENT_TYPES",
    "RELATION_CONVERTION", "RELATION_TYPES",
)
_CLASS_RE = re.compile(r"^class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:", re.M)
_ASSIGN_RE = re.compile(r"(?:\bself\.)?\b(%s)\s*=\s*\{" % "|".join(MAPPING_NAMES))
_SETTINGS_RE = re.compile(r"^def\s+integrationSettings\s*\(", re.M)
_SETTING_ITEM_RE = re.compile(r"""\[\s*['"](\w+)['"]\s*\]\s*=\s*([A-Za-z_]\w*)|['"](\w+)['"]\s*:\s*([A-Za-z_]\w*)""")


def _top_level_block(source, start):
    """The text from start to the next line written at column 0."""
    end = len(source)
    for match in re.finditer(r"^\S", source[start:], re.M):
        if match.start() > 0:
            end = start + match.start()
            break
    return source[start:end]


def _literal_dict(text, brace):
    """The dict literal opening at text[brace], or None when it is not a
    literal (a key such as BaseDbIntegration.documentName)."""
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                try:
                    value = ast.literal_eval(text[brace:index + 1])
                except (ValueError, SyntaxError):
                    return None
                return value if isinstance(value, dict) else None
    return None


def read_custom_mapping(source, cad):
    """The *_CONVERTION / *_TYPES dictionaries the CustomProcedure gives the
    CAD, as {name: dict}, and the warnings met reading them.

    The procedure is the client's Python 2 module, so it is never imported:
    its classes are found by their header, their dictionaries by their
    assignment (in __init__ or in the class body), a class inherits the
    dictionaries of its bases, and integrationSettings() says which class is
    the CAD's. A dictionary that is not a literal is skipped with a warning.
    """
    warnings = []
    classes = {}
    for match in _CLASS_RE.finditer(source):
        name, bases = match.group(1), match.group(2) or ""
        block = _top_level_block(source, match.start())
        mapping = {}
        for assign in _ASSIGN_RE.finditer(block):
            value = _literal_dict(block, assign.end() - 1)
            if value is None:
                warnings.append(_("CustomProcedure: %(name)s of %(cls)s is not a literal dictionary, skipped",
                                  name=assign.group(1), cls=name))
                continue
            mapping[assign.group(1)] = value
        classes[name] = ([base.strip().split(".")[-1] for base in bases.split(",") if base.strip()], mapping)

    def resolved(name, seen=()):
        if name not in classes or name in seen:
            return {}
        bases, own = classes[name]
        out = {}
        for base in bases:
            out.update(resolved(base, seen + (name,)))
        out.update(own)
        return out

    match = _SETTINGS_RE.search(source)
    if not match:
        warnings.append(_("CustomProcedure: no integrationSettings(), the default mapping is used"))
        return {}, warnings
    by_cad = {}
    for item in _SETTING_ITEM_RE.finditer(_top_level_block(source, match.start())):
        key = item.group(1) or item.group(3)
        by_cad[key.lower()] = item.group(2) or item.group(4)
    class_name = by_cad.get((cad or "").lower())
    if not class_name:
        warnings.append(_("CustomProcedure: integrationSettings() has no class for the CAD %(cad)r, "
                          "the default mapping is used", cad=cad))
        return {}, warnings
    if class_name not in classes:
        warnings.append(_("CustomProcedure: class %(cls)s not found, the default mapping is used",
                          cls=class_name))
        return {}, warnings
    return resolved(class_name), warnings


def flat_properties(properties):
    """{name.lower(): value} of every property set, the first set naming a
    property wins (as the converter's find_property does)."""
    out = {}
    for values in (properties or {}).values():
        if not isinstance(values, dict):
            continue
        for name, value in values.items():
            out.setdefault(str(name).lower(), value)
    return out


def _cast(value, kind):
    if value is None or kind in (None, "char"):
        return value if value is None else str(value)
    try:
        if kind == "int":
            return int(float(value))
        if kind == "float":
            return float(str(value).replace(",", "."))
        if kind == "bool":
            return str(value).strip().lower() in ("1", "true", "yes", "y", "si", "sì", "x")
    except (TypeError, ValueError):
        return None
    return value


def mapped_values(conversion, types, properties):
    """{odoo field: value} of the CAD properties a *_CONVERTION names."""
    out = {}
    for field_name, cad_name in (conversion or {}).items():
        if not isinstance(cad_name, str):
            continue
        if cad_name.lower() in properties:
            value = _cast(properties[cad_name.lower()], (types or {}).get(field_name))
            if value is not None:
                out[field_name] = value
    return out


class PlmGlbStructureImport(models.TransientModel):
    _name = "plm.glb.structure.import"
    _description = "Import a GLB structure (OmniaGLTFConverter zip)"

    zip_file = fields.Binary(string="Zip file", required=True)
    zip_name = fields.Char(string="File name")
    state = fields.Selection([("draft", "To import"), ("done", "Imported")], default="draft")
    result = fields.Text(string="Result", readonly=True)
    document_ids = fields.Many2many("ir.attachment", string="Documents", readonly=True)

    # ---------------------------------------------------------------- reading

    def _read_zip(self):
        self.ensure_one()
        try:
            archive = zipfile.ZipFile(io.BytesIO(self.zip_file.content))
        except zipfile.BadZipFile as ex:
            raise UserError(_("The file is not a zip: %s", ex)) from ex
        names = {name.rsplit("/", 1)[-1]: name for name in archive.namelist() if not name.endswith("/")}
        if STRUCTURE_FILE not in names:
            raise UserError(_("The zip holds no %s: it is not an OmniaGLTFConverter "
                              "\"All files with data\" export", STRUCTURE_FILE))
        try:
            structure = json.loads(archive.read(names[STRUCTURE_FILE]).decode("utf-8"))
        except ValueError as ex:
            raise UserError(_("%(file)s is not valid json: %(error)s", file=STRUCTURE_FILE, error=ex)) from ex
        if structure.get("schema") != STRUCTURE_SCHEMA:
            raise UserError(_("%(file)s has schema %(schema)r, %(expected)r expected",
                              file=STRUCTURE_FILE, schema=structure.get("schema"), expected=STRUCTURE_SCHEMA))
        documents = structure.get("documents") or {}
        if not documents:
            raise UserError(_("%s lists no document", STRUCTURE_FILE))
        for glb_name, entry in documents.items():
            if not entry.get("file_name"):
                raise UserError(_("The document %s of the json has no file_name: the CAD file name "
                                  "is required", glb_name))
            if not entry.get("engineering_code"):
                raise UserError(_("The document %s of the json has no engineering_code", glb_name))
            if glb_name not in names:
                raise UserError(_("The json names %s, which is not in the zip", glb_name))
        return archive, names, structure

    def _custom_procedure(self):
        """The CustomProcedure of the user, else of the first of their groups
        that has one (plm_client_customprocedure), as bytes; b"" without one.

        The priority is res.users.getCustomProcedure's, but that method keeps
        every group with custom_procedure != False, and an empty Binary is not
        False on Odoo 20: it answers the empty value of the first group."""
        user = self.env.user.sudo()
        if "custom_procedure" not in user._fields:
            return b""
        for record in [user, *user.group_ids]:
            value = record.custom_procedure
            if value:
                return value.content if hasattr(value, "content") else base64.b64decode(value)
        return b""

    def _custom_mapping(self, cad):
        """The mapping the CustomProcedure gives the CAD, and its warnings;
        ({}, []) without a procedure."""
        content = self._custom_procedure()
        if not content:
            return {}, []
        source = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
        return read_custom_mapping(source, cad)

    # -------------------------------------------------------------- importing

    def _product_values(self, entry, properties, mapping):
        values = mapped_values(mapping.get("COMPONENT_CONVERTION"), mapping.get("COMPONENT_TYPES"), properties)
        # The component's code is the document's unless the procedure maps
        # it to a property of its own
        values.setdefault("engineering_code", entry["engineering_code"])
        values.setdefault("engineering_revision", entry.get("engineering_revision") or 0)
        return values

    def _document_values(self, entry, properties, mapping):
        attachment = self.env["ir.attachment"]
        values = mapped_values(mapping.get("DOCUMENT_CONVERTION"), mapping.get("DOCUMENT_TYPES"), properties)
        values = {key: value for key, value in values.items() if key in attachment._fields}
        # The json's code and revision are the document's: the converter read
        # them from the properties it was set to
        values.update(engineering_code=entry["engineering_code"],
                      engineering_revision=entry.get("engineering_revision") or 0)
        return values

    def _native_document(self, entry, values, log):
        """The native CAD document of the entry: found by code and revision,
        else created empty, named as the CAD file, and checked out to the
        importing user so that their CAD client can save the file into it."""
        attachment = self.env["ir.attachment"]
        document = attachment.search([("engineering_code", "=", values["engineering_code"]),
                                      ("engineering_revision", "=", values["engineering_revision"])], limit=1)
        if document:
            writable = {key: value for key, value in values.items()
                        if key not in ("engineering_code", "engineering_revision")}
            if writable and document.engineering_state not in LOCKED_STATES:
                document.write(writable)
            return document
        document = attachment.create(dict(values, name=entry["file_name"], is_plm=True))
        self.env["plm.checkout"].create({"userid": self.env.uid, "documentid": document.id})
        log.append(_("%(file)s: native document %(code)s rev %(rev)s created, checked out to you",
                     file=entry["file_name"], code=document.engineering_code, rev=document.engineering_revision))
        return document

    def _glb_document(self, glb_name, content, native, product):
        """The .glb as a child of its native document (Web3DTree), linked to
        the component; a new import refreshes its content."""
        attachment = self.env["ir.attachment"]
        values = {"raw": content}
        if "source_convert_document" in attachment._fields:
            values.update(is_converted_document=True, source_convert_document=native.id)
        glb = attachment.search([("engineering_code", "=", glb_name), ("engineering_revision", "=", 0)], limit=1)
        if glb:
            glb.write(values)
        else:
            glb = attachment.create(dict(values, name=glb_name, engineering_code=glb_name,
                                         engineering_revision=0, is_plm=True))
        self.env["ir.attachment.relation"].saveDocumentRelationNew(native.id, glb.id, link_kind="Web3DTree")
        if product:
            self.env["plm.component.document.rel"].createFromIds(product, glb)
        return glb

    def action_import(self):
        self.ensure_one()
        archive, names, structure = self._read_zip()
        cad = structure.get("cad")
        mapping, log = self._custom_mapping(cad)
        if mapping:
            log.append(_("CustomProcedure of %(user)s used for the CAD %(cad)s", user=self.env.user.name, cad=cad))
        product_model = self.env["product.product"]
        documents = structure["documents"]
        nodes = {}
        natives = self.env["ir.attachment"]
        for glb_name, entry in documents.items():
            properties = flat_properties(entry.get("properties"))
            product = product_model.createFromProps(self._product_values(entry, properties, mapping))
            native = self._native_document(entry, self._document_values(entry, properties, mapping), log)
            if product:
                self.env["plm.component.document.rel"].createFromIds(product, native)
            self._glb_document(glb_name, archive.read(names[glb_name]), native, product)
            nodes[glb_name] = (product, native)
            natives |= native
        boms = 0
        for glb_name, entry in documents.items():
            children = entry.get("children") or []
            if entry.get("kind") != "assembly" or not children:
                continue
            product, native = nodes[glb_name]
            if not product:
                log.append(_("%s: no component, no BoM", entry["file_name"]))
                continue
            if product.engineering_state in LOCKED_STATES:
                log.append(_("%(file)s: component %(code)s is %(state)s, its BoM is left as it is",
                             file=entry["file_name"], code=product.engineering_code,
                             state=product.engineering_state))
                continue
            rows = []
            for child in children:
                child_node = nodes.get(child.get("glb"))
                if not child_node or not child_node[0]:
                    log.append(_("%(parent)s: child %(child)s has no file in the zip, left out of the BoM",
                                 parent=entry["file_name"], child=child.get("file_name") or child.get("glb")))
                    continue
                rows.append((child_node[0].id, child_node[1].id, {"product_qty": child.get("quantity") or 1}))
            if rows:
                self.env["mrp.bom"].saveRelationNew(((False, product.id, native.id), rows))
                boms += 1
        if "has_web3d" in natives._fields:
            # stored, and computed from the name only: the Web3DTree relation
            # just created does not trigger it
            self.env.add_to_compute(natives._fields["has_web3d"], natives)
        log.insert(0, _("%(docs)s documents imported from %(zip)s, %(boms)s BoM written",
                        docs=len(documents), zip=self.zip_name or STRUCTURE_FILE, boms=boms))
        self.write({"state": "done", "result": "\n".join(str(line) for line in log),
                    "document_ids": [(6, 0, natives.ids)]})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported documents"),
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.document_ids.ids)],
        }
