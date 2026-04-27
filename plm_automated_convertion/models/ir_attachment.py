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
import logging
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
import matplotlib.pyplot as plt
import matplotlib as mpl
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

except Exception as ex:
    logging.warning(ex)
try:
    from to_3mf.stl_to_3mf import stl_to_3mf
except Exception as ex:
    logging.warning(ex)
from .cad_excenge import convert as exConvert
from .cad_excenge import FORMAT_FROM as ex_from_format
from .cad_excenge import FORMAT_TO as ex_from_to

ALLOW_CONVERSION_FORMAT = [".dxf", 
                           ".obj", 
                           ".stp", 
                           ".step", 
                           ".stl"]

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
                #
                # Create a new plot
                #
                figure = plt.figure()
                axes = mplot3d.Axes3D(figure)
                #
                # Load the STL files and add the vectors to the plot
                #
                your_mesh = mesh.Mesh.from_file(stlName)
                axes.add_collection3d(mplot3d.art3d.Poly3DCollection(your_mesh.vectors))
                #
                # Auto scale to the mesh size
                #
                scale = your_mesh.points.flatten()
                axes.auto_scale_xyz(scale, scale, scale)
                #

                plt.savefig(newFileName, dpi=100, transparent=True)
                plt.close()
        except Exception as ex:
            raise UserError("Cannot convert due to error %r" % (ex))
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
                #
                # Create a new plot
                #
                figure = plt.figure()
                axes = mplot3d.Axes3D(figure)
                #
                # Load the STL files and add the vectors to the plot
                #
                your_mesh = mesh.Mesh.from_file(store_fname)
                axes.add_collection3d(mplot3d.art3d.Poly3DCollection(your_mesh.vectors))
                #
                # Auto scale to the mesh size
                #
                scale = your_mesh.points.flatten()
                axes.auto_scale_xyz(scale, scale, scale)
                #
    
                plt.savefig(newFileName, 
                            dpi=300, 
                            transparent=True)
                plt.close()
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

    def _updatePreview(self):
        for ir_attachment in self:
            store_fname = ir_attachment._full_path(ir_attachment.store_fname)
            if ".dxf" in ir_attachment.name.lower():
                ir_attachment._updatePreviewFromDxf(store_fname)
            if ".obj" in ir_attachment.name.lower():
                ir_attachment._updatePreviewFromObj(store_fname)
            if (
                ".stp" in ir_attachment.name.lower()
                or "step" in ir_attachment.name.lower()
            ):
                ir_attachment._updatePreviewFromStp(store_fname)
            if ".stl" in ir_attachment.name.lower():
                ir_attachment._updatePreviewFromStl(store_fname)

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

    @api.model_create_multi
    def create(self, vals):
        ret = super(ir_attachment, self).create(vals)
        ret.createPreviewStack()
        return ret

    def write(self, vals):
        ret = super(ir_attachment, self).write(vals)
        self.createPreviewStack()
        return ret
