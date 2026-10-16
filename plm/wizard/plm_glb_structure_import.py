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

The CAD properties go to Odoo fields through WEB_GLB_IMPORT, a dictionary
of this import alone, written in the CustomProcedure of the user, else of
their first group that has one:

    WEB_GLB_IMPORT = {
        "*": {"product": {"name": "Description"},          # every CAD
              "document": {"description": "Title"}},
        "solidworks": {"product": {"engineering_surface": "Finish"}},
    }

{odoo field: property name in the json} for the component and for the native
document, under "*" and under the json's "cad", the CAD's entries added to
"*" field by field; a value is converted to the type of its field. Nothing
else of the procedure is read: it is client code, so it is never run here,
and only that dictionary, written as a literal, is taken.
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
WEB_MAPPING_NAME = "WEB_GLB_IMPORT"
WEB_MAPPING_SECTIONS = ("product", "document")
_WEB_MAPPING_RE = re.compile(r"^%s\s*=\s*\{" % WEB_MAPPING_NAME, re.M)


def read_web_mapping(source):
    """The WEB_GLB_IMPORT dictionary of a CustomProcedure, or None when the
    procedure has none. It is read as text, never run, and must be a literal
    {cad or "*": {"product"|"document": {odoo field: property name}}}: a
    ValueError says what is wrong with it otherwise."""
    match = _WEB_MAPPING_RE.search(source)
    if not match:
        return None
    brace, depth = match.end() - 1, 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                break
    else:
        raise ValueError("%s has no closing brace" % WEB_MAPPING_NAME)
    try:
        mapping = ast.literal_eval(source[brace:index + 1])
    except (ValueError, SyntaxError) as ex:
        raise ValueError("%s is not a literal dictionary: %s" % (WEB_MAPPING_NAME, ex)) from ex
    for cad, sections in mapping.items():
        if not isinstance(cad, str) or not isinstance(sections, dict):
            raise ValueError("%s: %r must name a CAD and hold a dictionary" % (WEB_MAPPING_NAME, cad))
        for section, fields_map in sections.items():
            if section not in WEB_MAPPING_SECTIONS:
                raise ValueError("%s[%r]: %r is not one of %s"
                                 % (WEB_MAPPING_NAME, cad, section, ", ".join(WEB_MAPPING_SECTIONS)))
            if not isinstance(fields_map, dict) or not all(
                    isinstance(key, str) and isinstance(value, str) for key, value in fields_map.items()):
                raise ValueError("%s[%r][%r] must be {odoo field: property name}"
                                 % (WEB_MAPPING_NAME, cad, section))
    return mapping


def mapping_for_cad(mapping, cad):
    """{"product": {...}, "document": {...}} of the CAD: the "*" entries, the
    CAD's added to them field by field."""
    by_cad = {str(key).lower(): value for key, value in (mapping or {}).items()}
    out = {}
    for section in WEB_MAPPING_SECTIONS:
        out[section] = dict(by_cad.get("*", {}).get(section, {}))
        out[section].update(by_cad.get((cad or "").lower(), {}).get(section, {}))
    return out


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


TEXT_FIELD_TYPES = ("char", "text", "html", "selection")
WEB_FIELD_TYPES = TEXT_FIELD_TYPES + ("integer", "float", "monetary", "boolean")


def _cast(value, field_type):
    """The json value as the field type wants it; None when it cannot be."""
    if value is None:
        return None
    try:
        if field_type == "integer":
            return int(float(str(value).replace(",", ".")))
        if field_type in ("float", "monetary"):
            return float(str(value).replace(",", "."))
        if field_type == "boolean":
            return str(value).strip().lower() in ("1", "true", "yes", "y", "si", "sì", "x")
    except (TypeError, ValueError):
        return None
    return str(value)


def mapped_values(model, fields_map, properties):
    """{odoo field: value} of the json properties fields_map names, for the
    fields of model of a type the import writes."""
    out = {}
    for field_name, property_name in (fields_map or {}).items():
        field = model._fields.get(field_name)
        if field is None or field.type not in WEB_FIELD_TYPES:
            continue
        if property_name.lower() in properties:
            value = _cast(properties[property_name.lower()], field.type)
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
        """The CustomProcedure the CAD client gets, as bytes: the user's,
        else the first of their groups' (res.users.getCustomProcedure of
        plm_client_customprocedure, which sends base64); b"" without one."""
        if "custom_procedure" not in self.env["res.users"]._fields:
            return b""
        value, _file_name = self.env.user.getCustomProcedure()
        return base64.b64decode(value) if value else b""

    def _web_mapping(self, cad):
        """WEB_GLB_IMPORT of the CustomProcedure for the CAD, as
        {"product": {...}, "document": {...}}, and the lines to report."""
        empty = {section: {} for section in WEB_MAPPING_SECTIONS}
        content = self._custom_procedure()
        if not content:
            return empty, [_("No CustomProcedure: only code and revision are imported")]
        source = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
        try:
            mapping = read_web_mapping(source)
        except ValueError as ex:
            raise UserError(_("The CustomProcedure of %(user)s: %(error)s", user=self.env.user.name, error=ex)) from ex
        if mapping is None:
            return empty, [_("The CustomProcedure has no %s: only code and revision are imported", WEB_MAPPING_NAME)]
        mapping = mapping_for_cad(mapping, cad)
        log = [_("%(name)s of the CustomProcedure used for the CAD %(cad)s", name=WEB_MAPPING_NAME, cad=cad or "?")]
        # Fields the import cannot write are said once, not per document
        for section, model in (("product", "product.product"), ("document", "ir.attachment")):
            fields_map = self.env[model]._fields
            skipped = sorted(name for name in mapping[section]
                             if name not in fields_map or fields_map[name].type not in WEB_FIELD_TYPES)
            if skipped:
                log.append(_("%(name)s %(section)s: %(fields)s is not a field %(model)s has, or of a type "
                             "the import writes: ignored", name=WEB_MAPPING_NAME, section=section,
                             fields=", ".join(skipped), model=model))
        return mapping, log

    # -------------------------------------------------------------- importing

    def _product_values(self, entry, properties, mapping):
        values = mapped_values(self.env["product.product"], mapping["product"], properties)
        # The component's code is the document's unless the mapping takes it
        # from a property of its own
        values.setdefault("engineering_code", entry["engineering_code"])
        values.setdefault("engineering_revision", entry.get("engineering_revision") or 0)
        return values

    def _document_values(self, entry, properties, mapping):
        values = mapped_values(self.env["ir.attachment"], mapping["document"], properties)
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

    def _preview(self, entry, glb_name, archive, names, log):
        """The preview png of the entry, base64 text, or False: structure.json
        names it ("preview", <its .glb's name>.png) since the converter puts
        one beside each .glb; null, or a file not in the zip, is reported."""
        if "preview" not in entry:
            return False  # a zip written before the converter had previews
        png = entry.get("preview")
        if not png:
            log.append(_("%(glb)s: no preview in the zip", glb=glb_name))
            return False
        if png not in names:
            log.append(_("%(glb)s: its preview %(png)s is not in the zip", glb=glb_name, png=png))
            return False
        return base64.b64encode(archive.read(names[png])).decode()

    def action_import(self):
        self.ensure_one()
        archive, names, structure = self._read_zip()
        cad = structure.get("cad")
        mapping, log = self._web_mapping(cad)
        product_model = self.env["product.product"]
        documents = structure["documents"]
        nodes = {}
        natives = self.env["ir.attachment"]
        locked_previews = self.env["ir.attachment"]
        for glb_name, entry in documents.items():
            properties = flat_properties(entry.get("properties"))
            product = product_model.createFromProps(self._product_values(entry, properties, mapping))
            native = self._native_document(entry, self._document_values(entry, properties, mapping), log)
            if product:
                self.env["plm.component.document.rel"].createFromIds(product, native)
            glb = self._glb_document(glb_name, archive.read(names[glb_name]), native, product)
            preview = self._preview(entry, glb_name, archive, names, log)
            if preview:
                # The zip's preview replaces the document's, the CAD client's
                # included, but not on a released or obsoleted document
                glb.preview = preview
                if native.engineering_state in LOCKED_STATES:
                    if native not in locked_previews:
                        locked_previews |= native
                        log.append(_("%(file)s is %(state)s: its preview is left as it is",
                                     file=native.name, state=native.engineering_state))
                else:
                    native.preview = preview
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
            "view_mode": "kanban,list,form",
            # the PLM document views, which show the preview
            "views": [(self.env.ref("plm.document_kanban_view").id, "kanban"),
                      (self.env.ref("plm.ir_attachment_list").id, "list"),
                      (self.env.ref("plm.view_attachment_form_plm_hinerit").id, "form")],
            "domain": [("id", "in", self.document_ids.ids)],
            "context": {"odooPLM": True},
        }
