# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 03/nov/2016 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    info@omniasolutions.eu
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
Created on 03/nov/2016
@author: mboscolo
"""
import base64
import io
import json
import logging

_logger = logging.getLogger(__name__)

import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile

#
# conversion
#
from ezdxf import recover
from ezdxf.addons.drawing import matplotlib
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .obj2png import ObjFile
from stl import mesh
import matplotlib as mpl
mpl.use("Agg")  # non-interactive backend — required when running in Odoo worker threads
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d

try:
    import cadquery as cq
    from cadquery.occ_impl.importers.assembly import (
        _get_name, _get_ref_color, _get_material, _get_shape_color,
    )
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.TDocStd import TDocStd_Document
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.Interface import Interface_Static
    from cadquery.occ_impl.geom import Location
    from cadquery.occ_impl.shapes import Shape
    from cadquery.occ_impl.assembly import Color
except Exception as ex:
    logging.warning(ex)
try:
    from to_3mf.stl_to_3mf import stl_to_3mf
except Exception as ex:
    logging.warning(ex)

def _import_step_preserve_names(path: str) -> cq.Assembly:
    """Import a STEP file into a cq.Assembly using instance (comp_label) names.

    cadquery's built-in importStep uses the definition/template name (ref_name)
    for sub-assemblies, causing duplicate-name errors when the same part is placed
    multiple times. This function uses the instance label name (comp_name) instead,
    which is the name the CAD tool assigned to each individual placement.
    """
    step_reader = STEPCAFControl_Reader()
    step_reader.SetColorMode(True)
    step_reader.SetNameMode(True)
    step_reader.SetLayerMode(True)
    step_reader.SetSHUOMode(True)
    Interface_Static.SetIVal_s("read.stepcaf.subshapes.name", 1)

    status = step_reader.ReadFile(path)
    if status != IFSelect_RetDone:
        raise ValueError(f"Error reading STEP file: {path}")

    doc = TDocStd_Document(TCollection_ExtendedString("XmXCAF"))
    step_reader.Transfer(doc)

    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    def _process(lbl: TDF_Label, parent: cq.Assembly):
        comp_labels = TDF_LabelSequence()
        shape_tool.GetComponents_s(lbl, comp_labels)

        name_counter: dict = {}

        for i in range(comp_labels.Length()):
            comp_label = comp_labels.Value(i + 1)

            loc = shape_tool.GetLocation_s(comp_label)
            cq_loc = Location(loc) if loc else Location()

            if not shape_tool.IsReference_s(comp_label):
                continue

            ref_label = TDF_Label()
            shape_tool.GetReferredShape_s(comp_label, ref_label)
            color = _get_ref_color(comp_label)
            material = _get_material(comp_label)

            # Prefer the instance label name (unique per placement); fall
            # back to the definition/template name (the actual part name
            # from the CAD tool) when the instance label has no name.
            inst_name = (f"{_get_name(ref_label) or _get_name(comp_label)}:{i}")
            # Guarantee uniqueness within this parent level
            if inst_name in name_counter:
                name_counter[inst_name] += 1
                inst_name = f"{inst_name}_{name_counter[inst_name]}"
            else:
                name_counter[inst_name] = 0

            if shape_tool.IsAssembly_s(ref_label):
                sub = cq.Assembly(name=inst_name)
                _process(ref_label, sub)
                parent.add(sub, loc=cq_loc, name=inst_name,
                           color=color, material=material)

            elif shape_tool.IsSimpleShape_s(ref_label):
                final_shape = shape_tool.GetShape_s(ref_label)
                cq_shape = Shape.cast(final_shape)
                if color is None:
                    color = _get_shape_color(final_shape, color_tool)
                if material is None:
                    material = _get_material(ref_label)
                child = cq.Assembly(cq_shape, loc=cq_loc, name=inst_name,
                                    color=color, material=material)
                parent.add(child, name=inst_name)

    labels = TDF_LabelSequence()
    shape_tool.GetFreeShapes(labels)
    top_label = labels.Value(1)

    if shape_tool.IsReference_s(top_label):
        tmp = TDF_Label()
        shape_tool.GetReferredShape_s(top_label, tmp)
        top_label = tmp

    top_name = _get_name(top_label) or "root"
    assy = cq.Assembly(name=top_name)
    _process(top_label, assy)
    return assy

def _export_assembly_to_3mf(assembly, output_path):
    """Export a cq.Assembly to 3MF preserving the original component names.

    Traverses the assembly tree, tessellates each named leaf shape (with its
    accumulated world transform applied), and writes a valid 3MF ZIP with one
    named <object> per leaf.
    """
    parts = []

    def _collect(node, parent_loc):
        world_loc = parent_loc * node.loc
        if node.obj is not None:
            shape = node.obj.val() if isinstance(node.obj, cq.Workplane) else node.obj
            parts.append((node.name or f"part_{len(parts)}", shape, world_loc))
        for child in node.children:
            _collect(child, world_loc)

    _collect(assembly, cq.Location())

    NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    # Register as default namespace so ET writes <model> not <ns0:model>,
    # which is required for Three.js ThreeMFLoader's querySelectorAll('object').
    ET.register_namespace('', NS)

    def _tag(local):
        return f"{{{NS}}}{local}"

    model_elem = ET.Element(_tag("model"), {
        "unit": "millimeter",
        "xml:lang": "en-US",
    })
    resources_elem = ET.SubElement(model_elem, _tag("resources"))
    build_elem = ET.SubElement(model_elem, _tag("build"))

    for obj_id, (part_name, shape, world_loc) in enumerate(parts, start=1):
        try:
            verts, faces = shape.moved(world_loc).tessellate(0.1, 0.1)
        except Exception as ex:
            logging.warning("Skipping shape %r during 3MF tessellation: %s", part_name, ex)
            continue

        obj_elem = ET.SubElement(resources_elem, _tag("object"), {
            "id": str(obj_id),
            "name": part_name,
            "type": "model",
        })
        mesh_elem = ET.SubElement(obj_elem, _tag("mesh"))
        verts_elem = ET.SubElement(mesh_elem, _tag("vertices"))
        tris_elem = ET.SubElement(mesh_elem, _tag("triangles"))

        for v in verts:
            ET.SubElement(verts_elem, _tag("vertex"), {
                "x": str(round(v.x, 6)),
                "y": str(round(v.y, 6)),
                "z": str(round(v.z, 6)),
            })
        for tri in faces:
            ET.SubElement(tris_elem, _tag("triangle"), {
                "v1": str(tri[0]),
                "v2": str(tri[1]),
                "v3": str(tri[2]),
            })

        ET.SubElement(build_elem, _tag("item"), {"objectid": str(obj_id)})

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        '</Types>'
    )
    rels_content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        '</Relationships>'
    )
    model_bytes = io.BytesIO()
    ET.ElementTree(model_elem).write(model_bytes, encoding="UTF-8", xml_declaration=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels_content)
        zf.writestr("3D/3dmodel.model", model_bytes.getvalue())

from .cad_excenge import convert as exConvert
from .cad_excenge import FORMAT_FROM as ex_from_format
from .cad_excenge import FORMAT_TO as ex_from_to

ALLOW_CONVERSION_FORMAT = [".dxf",
                           ".obj",
                           ".stp",
                           ".step",
                           ".stl"]


def _render_stl_to_png(stl_path: str, png_path: str, dpi: int = 150) -> None:
    """Render an STL mesh to a PNG thumbnail.

    Uses matplotlib's 3D backend with explicit face/edge colours so the mesh
    is visible against a white background.  All callers should use this instead
    of inlining the Poly3DCollection logic to keep rendering consistent.
    """
    your_mesh = mesh.Mesh.from_file(stl_path)
    figure = plt.figure(figsize=(6, 6), facecolor="white")
    axes = figure.add_subplot(111, projection="3d")
    collection = mplot3d.art3d.Poly3DCollection(
        your_mesh.vectors,
        facecolor="#b0c4de",   # light steel-blue — neutral CAD-like colour
        edgecolor="none",
        alpha=1.0,
    )
    axes.add_collection3d(collection)
    scale = your_mesh.points.flatten()
    axes.auto_scale_xyz(scale, scale, scale)
    axes.set_facecolor("white")
    axes.view_init(elev=25, azim=45)
    axes.set_axis_off()
    plt.savefig(png_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(figure)


class ir_attachment(models.Model):
    _inherit = "ir.attachment"

    is_converted_document = fields.Boolean("Is Converted Document")
    source_convert_document = fields.Many2one(
        "ir.attachment", "Source Convert Document"
    )
    converted_documents = fields.One2many(
        "ir.attachment", "source_convert_document", "Converted documents"
    )

    def show_convert_wizard(self):
        context = dict(self.env.context or {})
        context["default_document_id"] = self.id
        context["name"] = self.name
        out = {
            "view_type": "form",
            "view_mode": "form",
            "res_model": "plm.convert",
            "view_id": self.env.ref("plm_automated_convertion.act_plm_convert_form").id,
            "type": "ir.actions.act_window",
            "context": context,
            "target": "new",
        }
        return out

    def checkParentCateg(self, categ):
        all_categs = categ
        for categ_id in categ.parent_id:
            all_categs += categ_id
            all_categs += self.checkParentCateg(categ_id)
        return all_categs

    def generateConvertedFiles(self):
        convert_stacks = self.env["plm.convert.stack"]
        for document in self:
            if document.document_type in ["2d", "3d"]:
                categ = self.env["product.category"]
                components = document.linkedcomponents.sorted(
                    lambda line: line.engineering_revision
                )
                if components:
                    component = components[0]
                    categ = component.categ_id
                convert_rule = self.env["plm.convert.rule"].sudo()
                convert_stack = self.env["plm.convert.stack"].sudo()
                _clean_name, ext = os.path.splitext(document.name)
                parent_categs = self.checkParentCateg(categ)
                rules = convert_rule.search(
                    [
                        ("product_category", "in", parent_categs.ids),
                        ("start_format", "ilike", ext),
                    ]
                )
                rules += convert_rule.search(
                    [
                        ("convert_alone_documents", "=", True),
                        ("start_format", "ilike", ext),
                    ]
                )
                for rule in rules:
                    if not components and not rule.convert_alone_documents:
                        continue
                    stacks = convert_stack.search(
                        [
                            ("start_format", "=", ext),
                            ("end_format", "=", rule.end_format),
                            ("start_document_id", "=", document.id),
                            ("server_id", "=", rule.server_id.id),
                            ("conversion_done", "=", False),
                        ]
                    )
                    if not stacks:
                        convert_stacks += convert_stack.create(
                            {
                                "start_format": ext,
                                "end_format": rule.end_format,
                                "product_category": categ.id,
                                "start_document_id": document.id,
                                "output_name_rule": rule.output_name_rule,
                                "server_id": rule.server_id.id,
                            }
                        )
                    else:
                        convert_stacks += stacks
        return convert_stacks

    def convert_from_dxf_to(self, toFormat):
        """
        convert using the exdxf library
        """
        if not self.store_fname:
            raise UserError(_("Cannot convert %s: no file content available.") % self.name)
        if toFormat.replace(".", "") not in ["png", "pdf", "svg", "jpg"]:
            raise UserError("Format %s not supported" % toFormat)

        store_fname = self._full_path(self.store_fname)

        doc, auditor = recover.readfile(store_fname)
        if not auditor.has_errors:
            tmpdirname = tempfile.gettempdir()
            name, exte = os.path.splitext(self.name)
            newFileName = os.path.join(tmpdirname, "%s%s" % (name, toFormat))
            matplotlib.qsave(doc.modelspace(), newFileName)
            return newFileName
        raise Exception(
            "Unable to perform the conversion Error: %s" % auditor.has_errors
        )

    def convert_from_obj_to(self, toFormat):
        """
        convert using the exdxf library
        """
        if not self.store_fname:
            raise UserError(_("Cannot convert %s: no file content available.") % self.name)
        if toFormat.replace(".", "") not in ["png", "pdf", "svg", "jpg"]:
            raise UserError("Format %s not supported" % toFormat)

        store_fname = self._full_path(self.store_fname)
        o = ObjFile(store_fname)
        tmpdirname = tempfile.gettempdir()
        name, exte = os.path.splitext(self.name)
        newFileName = os.path.join(tmpdirname, "%s%s" % (name, toFormat))
        o.Plot(newFileName, dpi=100)
        return newFileName

    def convert_from_step_to(self, toFormat):
        newFileName = ""
        try:
            if not self.store_fname:
                raise UserError(
                    _("Cannot convert %s: no file content available.") % self.name
                )
            if toFormat.replace(".", "").lower() not in [
                "png",
                "pdf",
                "svg",
                "jpg",
                "stl",
                "3mf",
                "gltf",
                "glb",
            ]:
                raise UserError("Format %s not supported" % toFormat)
            store_fname = self._full_path(self.store_fname)
            result = cq.importers.importStep(store_fname)
            name, exte = os.path.splitext(self.name)
            if ".3mf".lower() in toFormat:
                newFileName = os.path.join(tempfile.gettempdir(), "%s.3mf" % name)
                assembly = _import_step_preserve_names(store_fname)
                _export_assembly_to_3mf(assembly, newFileName)
                return newFileName
            if toFormat.lower() in [".gltf", ".glb"]:
                newFileName = os.path.join(tempfile.gettempdir(), "%s%s" % (name, toFormat.lower()))
                assembly = _import_step_preserve_names(store_fname)
                export_type = "GLB" if toFormat.lower() == ".glb" else "GLTF"
                assembly.save(newFileName, exportType=export_type)
                return newFileName
            with tempfile.TemporaryDirectory() as tmpdirname:
                name, exte = os.path.splitext(self.name)
                stlName = os.path.join(tmpdirname, "%s.stl" % name)
                cq.exporters.export(
                    result, stlName, tolerance=1.0, angularTolerance=1.0
                )
                newFileName = os.path.join(
                    tempfile.gettempdir(), "%s%s" % (name, toFormat)
                )
                if ".stl".lower() in toFormat:
                    shutil.copy(stlName, newFileName)
                    return newFileName
                _render_stl_to_png(stlName, newFileName)
        except Exception as ex:
            raise UserError(f"Cannot convert due to error {ex}" )
        return newFileName

    def convert_from_stl_to(self, toFormat):
        newFileName = ""
        if toFormat.replace(".", "").lower() not in ["png", 
                                                     "pdf", 
                                                     "svg", 
                                                     "jpg",
                                                     "3mf"]:
            raise UserError("Format %s not supported" % toFormat)
        store_fname = self._full_path(self.store_fname)
        with tempfile.TemporaryDirectory(delete=False ) as tmpdirname:
            name, exte = os.path.splitext(self.name)
            newFileName = os.path.join(tmpdirname, "%s%s" % (name, toFormat))
            if toFormat=='.3mf':
                stl_to_3mf([store_fname], 
                           newFileName)
            else:
                _render_stl_to_png(store_fname, newFileName)
        return newFileName

    def convert_to_format(self, toFormat, excangePath=None):
        """
        convert the attachment to the given format
        """
        obj_attachment = self.env["ir.attachment"]
        for ir_attachment in self:
            #
            # check before cad excange
            #
            name, exte = os.path.splitext(os.path.basename(ir_attachment.name))
            if (
                excangePath
                and os.path.exists(excangePath)
                and exte.lower() in ex_from_format
                and toFormat.lower() in ex_from_to
            ):
                with tempfile.TemporaryDirectory() as tmpdirname:
                    full_path_parent_target = os.path.join(
                        tmpdirname, ir_attachment.name
                    )
                    shutil.copy(
                        ir_attachment._full_path(ir_attachment.store_fname),
                        full_path_parent_target,
                    )
                    for docu_id_child_id in ir_attachment.getRelatedHiTree(
                        ir_attachment.id, True, True
                    ):
                        ir_attachment_child = obj_attachment.browse(docu_id_child_id)
                        full_path_child = obj_attachment._full_path(
                            ir_attachment_child.store_fname
                        )
                        shutil.copy(
                            full_path_child,
                            os.path.join(tmpdirname, ir_attachment_child.name),
                        )
                    return exConvert(excangePath, full_path_parent_target, toFormat)
            else:
                for extention in ALLOW_CONVERSION_FORMAT:
                    if extention in ir_attachment.name.lower():
                        if extention.lower() == ".dxf":
                            return ir_attachment.convert_from_dxf_to(toFormat)
                        elif extention.lower() == ".obj":
                            return ir_attachment.convert_from_obj_to(toFormat)
                        elif extention.lower() in [".stp", ".step"]:
                            return ir_attachment.convert_from_step_to(toFormat)
                        elif extention.lower() == ".stl":
                            return ir_attachment.convert_from_stl_to(toFormat)
                        else:
                            raise UserError(_("Format %s not supported") % toFormat)
            raise UserError(_("Format %s not supported") % toFormat)

    def _generate_step_preview_b64(self):
        """Render this STEP/STP attachment as a PNG thumbnail and return base64 bytes.

        Uses cadquery to load the geometry, tessellates to STL, then renders with
        matplotlib + numpy-stl.  Returns None on any failure so callers can fall
        back gracefully.
        """
        self.ensure_one()
        store_fname = self._full_path(self.store_fname)
        if not store_fname or not os.path.exists(store_fname):
            return None
        try:
            result = cq.importers.importStep(store_fname)
            with tempfile.TemporaryDirectory() as tmp:
                stl_path = os.path.join(tmp, "preview.stl")
                png_path = os.path.join(tmp, "preview.png")
                cq.exporters.export(result, stl_path, tolerance=1.0, angularTolerance=1.0)
                _render_stl_to_png(stl_path, png_path)
                with open(png_path, "rb") as f:
                    return base64.b64encode(f.read())
        except Exception as ex:
            _logger.warning("STEP preview generation failed for %r: %s", self.name, ex)
            plt.close("all")
            return None

    def action_update_preview(self):
        """Public action for the 'Update Preview' button on the form/list view."""
        self._updatePreview()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Preview Updated"),
                "message": _("Preview image has been regenerated."),
                "type": "success",
                "sticky": False,
            },
        }

    def _updatePreview(self):
        for ir_attachment in self:
            if not ir_attachment.store_fname:
                continue
            lower_name = ir_attachment.name.lower() if ir_attachment.name else ""
            store_fname = ir_attachment._full_path(ir_attachment.store_fname)
            if ".dxf" in lower_name:
                ir_attachment._updatePreviewFromDxf(store_fname)
            if ".obj" in lower_name:
                ir_attachment._updatePreviewFromObj(store_fname)
            if ".stp" in lower_name or ".step" in lower_name:
                ir_attachment._updatePreviewFromStp(store_fname)
            if ".stl" in lower_name:
                ir_attachment._updatePreviewFromStl(store_fname)
            if any(ext in lower_name for ext in (".3mf", ".gltf", ".glb")):
                source = ir_attachment.source_convert_document
                if source and any(
                    ext in (source.name or "").lower() for ext in (".stp", ".step")
                ):
                    preview = source._generate_step_preview_b64()
                    if preview:
                        ir_attachment.preview = preview

    def _updatePreviewFromStl(self, fromFile):
        with tempfile.TemporaryDirectory() as tmpdirname:
            name, exte = os.path.splitext(self.name)
            os.path.join(tmpdirname, "%s.png" % name)
            converted_file = self.convert_from_stl_to(".png")
            with open(converted_file, "rb") as pngStream:
                self.preview = base64.b64encode(pngStream.read())

    def _updatePreviewFromStp(self, fromFile):
        with tempfile.TemporaryDirectory() as tmpdirname:
            name, exte = os.path.splitext(self.name)
            os.path.join(tmpdirname, "%s.png" % name)
            converted_file = self.convert_from_step_to(".png")
            with open(converted_file, "rb") as pngStream:
                self.preview = base64.b64encode(pngStream.read())

    def _updatePreviewFromObj(self, fromFile):
        with tempfile.TemporaryDirectory() as tmpdirname:
            name, exte = os.path.splitext(self.name)
            os.path.join(tmpdirname, "%s.png" % name)
            converted_file = self.convert_from_obj_to(".png")
            with open(converted_file, "rb") as pngStream:
                self.preview = base64.b64encode(pngStream.read())

    def _updatePreviewFromDxf(self, fromFile):
        doc, auditor = recover.readfile(fromFile)
        if not auditor.has_errors:
            with tempfile.TemporaryDirectory() as tmpdirname:
                name, exte = os.path.splitext(self.name)
                pngName = os.path.join(tmpdirname, "%s.png" % name)
                matplotlib.qsave(doc.modelspace(), pngName)
                pdfName = os.path.join(tmpdirname, "%s.pdf" % name)
                matplotlib.qsave(doc.modelspace(), pdfName)
                with open(pngName, "rb") as pngStream:
                    self.preview = base64.b64encode(pngStream.read())
                with open(pdfName, "rb") as pdfStream:
                    self.printout = base64.b64encode(pdfStream.read())

    def createPreviewStack(self):
        obj_stack = self.env["plm.convert.stack"]
        for ir_attachment in self:
            for extention in ALLOW_CONVERSION_FORMAT:
                if extention in ir_attachment.name.lower():
                    if not obj_stack.search_count(
                        [
                            ("start_document_id", "=", ir_attachment.id),
                            ("operation_type", "=", "UPDATE"),
                        ]
                    ):
                        conv_format = self.checkCreateDefaultPreviewFormat(extention)
                        obj_stack.create(
                            {
                                "operation_type": "UPDATE",
                                "start_document_id": ir_attachment.id,
                                "convrsion_rule": conv_format.id,
                            }
                        )

    def checkCreateDefaultPreviewFormat(self, start_format):
        format_model = self.env["plm.convert.format"]

        if start_format.upper() in [".STP"]:
            format_model = self.env.ref(
                "plm_automated_convertion.update_stp_preview_png"
            )
        elif start_format.upper() in [".STEP"]:
            format_model = self.env.ref(
                "plm_automated_convertion.update_step_preview_png"
            )
        elif start_format.upper() in [".DXF"]:
            format_model = self.env.ref(
                "plm_automated_convertion.update_dxf_preview_png"
            )
        elif start_format.upper() in [".OBJ"]:
            format_model = self.env.ref(
                "plm_automated_convertion.update_obj_preview_png"
            )
        elif start_format.upper() in [".STL"]:
            format_model = self.env.ref(
                "plm_automated_convertion.update_stl_preview_png"
            )
        else:
            if not start_format:
                format_ids = format_model.search(
                    [
                        ("end_format", "=", ".png"),
                        ("start_format", "=", start_format),
                        ("available", "=", True),
                    ]
                )
                for format in format_ids:
                    format_model = format
                    break
        return format_model

    def split_step_assembly(self):
        """
        Split a STEP assembly into one ir.attachment per unique direct child.

        For each unique child (identified by its STEP instance name):
        - Counts occurrences across all placements (used as BOM line qty).
        - Exports the child geometry to a new STEP file.
        - Creates (or reuses by engineering_code) an ir.attachment.
        - Establishes an HiTree document relation: assembly → child part.
        - Finds a product.product matching the engineering_code, or creates one.
        - Links the child attachment to the product via linkedcomponents.

        After processing all children:
        - Finds or creates a product for the assembly itself.
        - Finds or creates a manufacturing BOM (type "normal") for that product.
        - Creates BOM lines for each child product with the correct quantity.
        """
        self.ensure_one()
        if not any(ext in self.name.lower() for ext in [".stp", ".step"]):
            raise UserError(_("Split is only available for STEP (.step / .stp) files."))

        store_fname = self._full_path(self.store_fname)
        if not store_fname or not os.path.exists(store_fname):
            raise UserError(_("The STEP file cannot be found in the file store."))

        try:
            assembly = _import_step_preserve_names(store_fname)
        except Exception as ex:
            raise UserError(_("Cannot read the STEP assembly: %s") % ex)

        IrAttachmentRelation = self.env["ir.attachment.relation"]
        ProductTemplate = self.env["product.template"]
        ProductProduct = self.env["product.product"]
        MrpBom = self.env["mrp.bom"]
        MrpBomLine = self.env["mrp.bom.line"]

        # Build an ordered map: clean_name → (first_node, occurrence_count)
        # _import_step_preserve_names appends ":N" for duplicate placements.
        child_info = {}
        for child_node in assembly.children:
            raw_name = child_node.name or ""
            clean_name = raw_name.rsplit(":", 1)[0] if ":" in raw_name else raw_name
            if not clean_name:
                continue
            if clean_name not in child_info:
                child_info[clean_name] = {"node": child_node, "qty": 1}
            else:
                child_info[clean_name]["qty"] += 1

        created_attachments = self.env["ir.attachment"]
        child_products = []  # [(product, qty), ...]

        for clean_name, info in child_info.items():
            child_node = info["node"]
            qty = info["qty"]

            # Export child geometry to a temporary STEP file
            tmp_path = None
            step_b64 = None
            try:
                fd, tmp_path = tempfile.mkstemp(suffix=".step")
                os.close(fd)

                if child_node.obj is not None:
                    # Leaf shape: wrap in a neutral-named root so the child name
                    # does not collide with the assembly's own entry in _query.
                    new_assy = cq.Assembly(name="root")
                    new_assy.add(child_node.obj, name=clean_name, color=child_node.color)
                    new_assy.save(tmp_path, exportType="STEP")
                else:
                    # Sub-assembly: save directly to avoid the "Unique name required"
                    # error that occurs when iterating .children and re-adding them —
                    # .children yields objects whose .name is the definition name
                    # (shared across all placements), not the unique instance name.
                    child_node.save(tmp_path, exportType="STEP")

                with open(tmp_path, "rb") as f:
                    step_b64 = base64.b64encode(f.read())
            except Exception as ex:
                _logger.warning("Skipping child %r — could not export STEP: %s", clean_name, ex)
                continue
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

            # Reuse an existing attachment with the same engineering_code, or create one
            child_attachment = self.search(
                [("engineering_code", "=", clean_name), ("id", "!=", self.id)],
                order="engineering_revision DESC",
                limit=1,
            )
            if child_attachment:
                child_attachment.write({"datas": step_b64})
            else:
                child_attachment = self.create(
                    {
                        "name": f"{clean_name}.step",
                        "datas": step_b64,
                        "engineering_code": clean_name,
                        "is_plm": True,
                        "is_converted_document": True,
                        "source_convert_document": self.id,
                    }
                )

            # Document relation: parent assembly → child part (HiTree)
            IrAttachmentRelation.saveDocumentRelationNew(
                self.id, child_attachment.id, "HiTree"
            )

            # Find or create a product for this child
            product = ProductProduct.search(
                [("engineering_code", "=", clean_name)],
                order="engineering_revision DESC",
                limit=1,
            )
            if not product:
                # Create a minimal product.template; Odoo auto-creates product.product
                tmpl = ProductTemplate.create(
                    {
                        "name": clean_name,
                        "engineering_code": clean_name,
                    }
                )
                product = ProductProduct.search(
                    [("product_tmpl_id", "=", tmpl.id)],
                    limit=1,
                )

            if product:
                child_attachment.write({"linkedcomponents": [(4, product.id)]})
                child_products.append((product, qty))

            created_attachments |= child_attachment

        if not created_attachments:
            raise UserError(
                _("No splittable children were found in the STEP assembly.")
            )

        # --- BOM creation ---
        # Find or create a product for the assembly (self) if not already linked.
        assy_product = self.linkedcomponents[:1]
        if not assy_product and self.engineering_code:
            assy_product = ProductProduct.search(
                [("engineering_code", "=", self.engineering_code)],
                order="engineering_revision DESC",
                limit=1,
            )
        if not assy_product:
            assy_name = os.path.splitext(self.name)[0]
            eng_code = self.engineering_code or assy_name
            tmpl = ProductTemplate.create(
                {
                    "name": assy_name,
                    "engineering_code": eng_code,
                }
            )
            assy_product = ProductProduct.search(
                [("product_tmpl_id", "=", tmpl.id)],
                limit=1,
            )
            if assy_product:
                self.write({"linkedcomponents": [(4, assy_product.id)]})

        if assy_product and child_products:
            bom = MrpBom.search(
                [
                    ("product_tmpl_id", "=", assy_product.product_tmpl_id.id),
                    ("type", "=", "normal"),
                ],
                limit=1,
            )
            if not bom:
                bom = MrpBom.create(
                    {
                        "product_tmpl_id": assy_product.product_tmpl_id.id,
                        "product_id": assy_product.id,
                        "type": "normal",
                        "product_qty": 1.0,
                    }
                )

            # Replace BOM lines for the children being imported
            imported_product_ids = {p.id for p, _ in child_products}
            bom.bom_line_ids.filtered(
                lambda l: l.product_id.id in imported_product_ids
            ).unlink()
            for child_product, qty in child_products:
                MrpBomLine.create(
                    {
                        "bom_id": bom.id,
                        "product_id": child_product.id,
                        "product_qty": float(qty),
                    }
                )

        return {
            "type": "ir.actions.act_window",
            "name": _("STEP Assembly Children"),
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "domain": [("id", "in", created_attachments.ids)],
        }

    def _build_step_json_tree(self, assembly, split=False, is_root=False,
                               datas_map=None, tmp_dir=None, parent_name="", child_index=0,
                               ancestor_codes=frozenset(), selected_clean_names=None):
        """Recursively convert a cq.Assembly node into a saveStructure JSON node.

        engineering_code  ← clean instance name (no :N suffix)
        product name      ← same (STEP rarely carries a separate description)
        When split=True the node's geometry is exported to a temp file inside
        tmp_dir.  The path is stored in datas_map[eng_code] so the caller can
        read and write it to the attachment just-in-time, avoiding keeping the
        entire base64 payload in memory across all nodes simultaneously.
        datas is intentionally NOT put into DOCUMENT_ATTRIBUTES / the JSON tree.
        """
        raw_name = assembly.name or ""
        clean_name = raw_name.rsplit(":", 1)[0] if ":" in raw_name else raw_name
        if not clean_name:
            if is_root:
                clean_name = os.path.splitext(self.name)[0]
            else:
                clean_name = f"{parent_name}_{child_index}"
        elif not is_root and clean_name in ancestor_codes:
            # Non-empty name that collides with an ancestor's engineering_code.
            # The parent already assigned an unnamed_idx counter; use it to
            # build a unique name so this node doesn't map to the same DB
            # record as its ancestor and trigger a self-referencing relation.
            base = child_index or 1
            while f"{parent_name}_{base}" in ancestor_codes:
                base += 1
            clean_name = f"{parent_name}_{base}"

        if not is_root and selected_clean_names is not None and clean_name not in selected_clean_names:
            return None

        if is_root:
            # Prefer engineering_code/revision from the already-linked product so
            # saveStructure finds the right record without a revision mismatch.
            linked = self.linkedcomponents[:1]
            if linked:
                eng_code = linked.engineering_code or self.engineering_code or clean_name
                eng_rev = linked.engineering_revision
            else:
                eng_code = self.engineering_code or clean_name
                eng_rev = 0
        else:
            eng_code = clean_name
            eng_rev = 0

        if split and not is_root and tmp_dir is not None and datas_map is not None:
            tmp_path = os.path.join(tmp_dir, f"{clean_name}.step")
            try:
                if assembly.obj is not None:
                    # Leaf shape: wrap in a neutral-named root so the child name
                    # does not collide with the assembly's own entry in _query.
                    wrapper = cq.Assembly(name="root")
                    wrapper.add(assembly.obj, name=clean_name, color=assembly.color)
                    wrapper.save(tmp_path, exportType="STEP")
                else:
                    # Sub-assembly: save the node directly.
                    # Copying children via assembly.children would use each child's
                    # definition .name (shared by all placements of the same part)
                    # instead of the unique instance name stored in the parent
                    # _query, causing "Unique name is required" errors.
                    assembly.save(tmp_path, exportType="STEP")
                datas_map[eng_code] = tmp_path
            except Exception as ex:
                _logger.warning("Could not export STEP for %r: %s", clean_name, ex)

        # Root document is intentionally excluded from the tree: saveStructure
        # runs canBeSaved(raiseError=True) on the root DOCUMENT_ATTRIBUTES, which
        # requires a live checkout.  We don't want to check out/in the source
        # document during BOM recovery, so we only pass PRODUCT_ATTRIBUTES for
        # the root.  BOM lines use child document IDs as source_id.
        doc_attrs = None if is_root else {
            "engineering_code": eng_code,
            "engineering_revision": eng_rev,
            "name": f"{clean_name}.step",
            "is_plm": True,
            "SKIP_CHECKOUT": True,
        }

        product_attrs = {
            "engineering_code": eng_code,
            "name": eng_code,
            "engineering_revision": eng_rev,
        }

        # Deduplicate children by clean name, counting occurrences for qty.
        # Unnamed children (empty clean name) or children whose name collides with
        # an ancestor's engineering_code get a unique key; their real name is
        # resolved during the recursive call using parent_name + child_index,
        # which prevents saveStructure from mapping them to the same DB record as
        # the ancestor and triggering the ir_attachment_relation self-reference check.
        child_info = {}
        unnamed_idx = 0
        blocked_codes = ancestor_codes | {eng_code}
        for child in assembly.children:
            child_raw = child.name or ""
            child_clean = child_raw.rsplit(":", 1)[0] if ":" in child_raw else child_raw
            if not child_clean or child_clean in blocked_codes:
                unnamed_idx += 1
                child_info[f"__unnamed_{unnamed_idx}"] = {
                    "node": child, "qty": 1, "unnamed_idx": unnamed_idx,
                }
                continue
            if child_clean not in child_info:
                child_info[child_clean] = {"node": child, "qty": 1}
            else:
                child_info[child_clean]["qty"] += 1

        relations = []
        for info in child_info.values():
            child_tree = self._build_step_json_tree(
                info["node"], split=split, is_root=False,
                datas_map=datas_map, tmp_dir=tmp_dir,
                parent_name=clean_name, child_index=info.get("unnamed_idx", 0),
                ancestor_codes=blocked_codes,
                selected_clean_names=selected_clean_names,
            )
            if child_tree:
                child_tree["FORCE_QTY"] = info["qty"]
                child_tree["MRP_ATTRIBUTES"] = {"product_qty": info["qty"]}
                relations.append(child_tree)

        node = {
            "PRODUCT_ATTRIBUTES": product_attrs,
            "CREATE_BOM": bool(relations),
            "RELATIONS": relations,
            "DOC_TYPE": "3D",
        }
        if doc_attrs:
            node["FILE_PATH"] = "virtual"
            node["DOCUMENT_ATTRIBUTES"] = doc_attrs
        return node

    def recover_bom_from_step(self, split=False, generate_preview=False, selected_clean_names=None):
        """Parse this STEP attachment and create/update products + multi-level BOM.

        Uses saveStructure so find-or-create logic for documents, products,
        document relations and BOM lines is handled in one consistent pass.
        split=True exports every assembly node as a child STEP file inside a
        temporary directory.  After saveStructure the files are read one at a
        time and written to the attachment, so only one file is in memory at
        a time regardless of assembly size.
        generate_preview=True regenerates PNG previews for all affected documents.
        """
        self.ensure_one()
        lower_name = (self.name or "").lower()
        if not any(ext in lower_name for ext in [".stp", ".step"]):
            raise UserError(_("BOM recovery is only available for STEP files."))

        store_fname = self._full_path(self.store_fname)
        if not store_fname or not os.path.exists(store_fname):
            raise UserError(_("The STEP file cannot be found in the file store."))

        try:
            assembly = _import_step_preserve_names(store_fname)
        except Exception as ex:
            raise UserError(_("Cannot read STEP assembly: %s") % ex)

        if selected_clean_names is not None:
            selected_clean_names = set(selected_clean_names)

        with tempfile.TemporaryDirectory() as tmp_dir:
            datas_map = {} if split else None
            tree = self._build_step_json_tree(
                assembly, split=split, is_root=True,
                datas_map=datas_map, tmp_dir=tmp_dir,
                selected_clean_names=selected_clean_names,
            )
            self.env["ir.attachment"].saveStructure([json.dumps(tree), "", "", True])

            # Write STEP content to child attachments one file at a time.
            # saveStructure creates new records without file content (datas is not
            # in the tree) and skips existing ones (no checkout → needUpdate=False),
            # so we force-write here for both cases.
            if datas_map:
                for eng_code, tmp_path in datas_map.items():
                    if not os.path.exists(tmp_path):
                        continue
                    child_docs = self.search([("engineering_code", "=", eng_code)])
                    if not child_docs:
                        continue
                    with open(tmp_path, "rb") as fh:
                        child_docs.write({"datas": base64.b64encode(fh.read())})
            # tmp_dir and all exported STEP files are deleted here

        if generate_preview:
            self._updatePreview()
            if split and datas_map:
                child_docs = self.search([
                    ("engineering_code", "in", list(datas_map.keys())),
                    ("id", "!=", self.id),
                    ("store_fname", "!=", False),
                ])
                child_docs._updatePreview()

        return True

    def action_view_step_tree(self):
        """Open the interactive STEP structure viewer in a new browser tab."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/plm/step_tree/{self.id}",
            "target": "new",
        }

    @api.model_create_multi
    def create(self, vals):
        ret = super(ir_attachment, self).create(vals)
        ret.createPreviewStack()
        return ret

    def write(self, vals):
        ret = super(ir_attachment, self).write(vals)
        self.createPreviewStack()
        return ret
