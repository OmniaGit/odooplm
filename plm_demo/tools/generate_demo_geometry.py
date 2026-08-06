#!/usr/bin/env python3
"""Generate the OdooPLM demo dataset: geometry, drawings, previews and metadata.

Everything the demo module installs is produced here, so the provenance of every
published file is this script — no third party CAD, no licensing question.

Run it inside the OdooPLM image, which already has cadquery, ezdxf, matplotlib
and numpy-stl:

    docker run --rm --user 0 \
        -v $PWD:/plm_demo \
        --entrypoint python3 ghcr.io/omniagit/odooplm:19.0 \
        /plm_demo/tools/generate_demo_geometry.py --out /plm_demo

It writes ``data/dataset.json`` plus ``files/{documents,previews,images,markups}``,
in exactly the shape ``hooks.py`` loads.

The product is a linear shaft support unit: a base plate carrying two bearing
units on a common shaft. Three BOM levels, a spare part BOM for the wear items,
2D drawings for the machined parts, and two 3D markups on the top assembly.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import zipfile

import numpy as np
import cadquery as cq
from cadquery import exporters

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt              # noqa: E402
from mpl_toolkits import mplot3d             # noqa: E402
from stl import mesh as stlmesh              # noqa: E402

STEEL = 7.85e-6          # kg/mm3
CAST_IRON = 7.20e-6
BRONZE = 8.80e-6
ALUMINIUM = 2.70e-6

MESH_TOLERANCE = 0.12    # coarse on purpose: the demo ships in a git repository


# ---------------------------------------------------------------- geometry ---
def bearing_housing():
    """Foot mounted shaft support block: bore along X, so a shaft runs through it."""
    block = cq.Workplane("XY").box(30, 70, 56, centered=(True, True, False))
    block = block.edges("|X and >Z").fillet(10)
    # bore and bushing seats, along X
    bore = (cq.Workplane("XY").circle(15).extrude(60)
            .rotate((0, 0, 0), (0, 1, 0), 90).translate((-30, 0, 34)))
    seat = (cq.Workplane("XY").circle(21).extrude(12)
            .rotate((0, 0, 0), (0, 1, 0), 90).translate((3, 0, 34)))
    seat2 = (cq.Workplane("XY").circle(21).extrude(12)
             .rotate((0, 0, 0), (0, 1, 0), -90).translate((-3, 0, 34)))
    block = block.cut(bore).cut(seat).cut(seat2)
    # mounting holes through the foot
    block = (block.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .pushPoints([(0, 27), (0, -27)]).circle(4.5).cutThruAll())
    return block.faces(">Z").edges("%CIRCLE").chamfer(0.8)


def cover():
    return (
        cq.Workplane("XY").circle(45).extrude(8)
        .faces(">Z").workplane().circle(21).cutBlind(-4)
        .faces("<Z").workplane().polarArray(35, 45, 360, 4).circle(3.5).cutThruAll()
        .edges("%CIRCLE and >Z").fillet(1.0)
    )


def bushing():
    return (cq.Workplane("XY").circle(21).extrude(24)
            .faces(">Z").workplane().circle(15).cutThruAll()
            .edges("%CIRCLE").chamfer(0.8))


def shaft():
    part = cq.Workplane("XY").circle(14.95).extrude(260)
    part = part.faces(">Z").chamfer(1.5).faces("<Z").chamfer(1.5)
    # keyway, cut with a solid: a cylindrical face cannot carry a workplane
    keyway = cq.Workplane("XY").box(6, 8, 45).translate((0, 12.0, 225))
    return part.cut(keyway)


def base_plate():
    plate = cq.Workplane("XY").box(300, 120, 20, centered=(True, True, False))
    plate = plate.edges("|Z").fillet(12)
    plate = (plate.faces(">Z").workplane()
             .pushPoints([(x, y) for x in (-127, -73, 73, 127) for y in (-27, 27)])
             .circle(4.5).cutThruAll())
    return plate.faces(">Z").edges("%CIRCLE").chamfer(0.8)


def clamp_ring():
    ring = (cq.Workplane("XY").circle(28).extrude(14)
            .faces(">Z").workplane().circle(15).cutThruAll())
    # clamping slit, cut through the wall on one side
    slit = cq.Workplane("XY").box(3, 20, 14).translate((0, 19, 7))
    ring = ring.cut(slit)
    return ring.edges("%CIRCLE and >Z").chamfer(0.8)


def hex_screw(diameter, length):
    head = (cq.Workplane("XY").polygon(6, diameter * 1.7).extrude(diameter * 0.65))
    shank = (cq.Workplane("XY").circle(diameter / 2)
             .extrude(-length).faces("<Z").chamfer(diameter * 0.12))
    return head.union(shank)


def spacer():
    return (cq.Workplane("XY").circle(21).extrude(6)
            .faces(">Z").workplane().circle(15.5).cutThruAll())


def end_cap():
    return (cq.Workplane("XY").circle(26).extrude(6)
            .faces(">Z").workplane().circle(20).cutBlind(-3)
            .edges("%CIRCLE and >Z").fillet(1.0))


# ------------------------------------------------------------- part catalog ---
# code, name, builder, material, density, drawing?
CATALOG = [
    ("BRG-HSG-001", "Bearing housing 90", bearing_housing, "EN-GJL-250", CAST_IRON, True),
    ("CVR-090-001", "Bearing cover 90", cover, "EN-GJL-250", CAST_IRON, False),
    ("BSH-030-001", "Bronze bushing 30x42x24", bushing, "CuSn12", BRONZE, False),
    ("SPC-030-001", "Spacer ring 30x42x6", spacer, "C45", STEEL, False),
    ("CAP-052-001", "End cap 52", end_cap, "EN AW-6082", ALUMINIUM, False),
    ("SCR-M6-020", "Hex screw M6x20", lambda: hex_screw(6, 20), "8.8 zinc plated", STEEL, False),
    ("SCR-M8-030", "Hex screw M8x30", lambda: hex_screw(8, 30), "8.8 zinc plated", STEEL, False),
    ("SHF-020-001", "Drive shaft 30x260", shaft, "42CrMo4", STEEL, True),
    ("CLP-020-001", "Shaft clamp ring 30", clamp_ring, "C45", STEEL, False),
    ("BASE-100", "Base plate 300x120", base_plate, "S235JR", STEEL, True),
]

# assembly, name, [(child code, qty)]
ASSEMBLIES = [
    ("BRG-UNIT-001", "Bearing unit 30 complete", [
        ("BRG-HSG-001", 1), ("BSH-030-001", 1), ("SPC-030-001", 1),
        ("CVR-090-001", 1), ("CAP-052-001", 1), ("SCR-M6-020", 4)]),
    ("LSU-100", "Linear shaft support unit", [
        ("BASE-100", 1), ("BRG-UNIT-001", 2), ("SHF-020-001", 1),
        ("CLP-020-001", 2), ("SCR-M8-030", 8)]),
]

# parts that are consumed in service -> spare part BOM of the bearing unit
SPARES = ("BSH-030-001", "SPC-030-001", "SCR-M6-020")

# assemblies that get a ballooned 2D sheet: the root of the spare BOM, which the
# Spare Parts Manual prints, and the top assembly, which is what a customer asks
# for first. Their drawings are the ones flagged used_for_spare.
ASSEMBLY_DRAWINGS = ("BRG-UNIT-001", "LSU-100")

DRAWN = tuple(code for code, _n, _b, _m, _d, drawing in CATALOG if drawing)


# ---------------------------------------------------------------- exporting ---
def slug(value):
    out = "".join(c if c.isalnum() else "_" for c in value.lower())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def write_3mf(stl_path, target, title):
    """3MF is a zip around one XML mesh — small, single file, and the viewer reads it."""
    m = stlmesh.Mesh.from_file(stl_path)
    tris = m.vectors.reshape(-1, 3)
    verts, index = np.unique(np.round(tris, 3), axis=0, return_inverse=True)
    faces = index.reshape(-1, 3)
    model = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
        '<metadata name="Title">%s</metadata>' % title,
        '<metadata name="Designer">OmniaSolutions</metadata>',
        '<metadata name="Application">OdooPLM demo generator</metadata>',
        '<metadata name="LicenseTerms">AGPL-3.0-or-later</metadata>',
        '<resources><object id="1" type="model"><mesh><vertices>',
    ]
    model += ['<vertex x="%.3f" y="%.3f" z="%.3f"/>' % tuple(v) for v in verts]
    model.append("</vertices><triangles>")
    model += ['<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in faces]
    model.append("</triangles></mesh></object></resources><build><item objectid=\"1\"/></build></model>")

    types = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
             "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", "".join(model))


def render(stl_path, target, size=(4.6, 3.8), dpi=110, elev=24, azim=-58):
    m = stlmesh.Mesh.from_file(stl_path)
    normals = m.normals / (np.linalg.norm(m.normals, axis=1)[:, None] + 1e-9)
    light = np.array([0.4, -0.5, 0.77])
    light = light / np.linalg.norm(light)
    shade = np.clip(normals @ light, 0, 1) * 0.6 + 0.4
    colors = np.clip(shade[:, None] * np.array([0.46, 0.53, 0.62])[None, :] * 1.75, 0, 1)

    fig = plt.figure(figsize=size, facecolor="white")
    ax = fig.add_subplot(projection="3d")
    ax.add_collection3d(mplot3d.art3d.Poly3DCollection(
        m.vectors, facecolors=colors, edgecolors="none", shade=False))
    pts = m.points.reshape(-1, 3)
    center = pts.mean(axis=0)
    radius = np.abs(pts - center).max() * 0.62
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()
    ax.view_init(elev=elev, azim=azim)
    fig.tight_layout(pad=0)
    fig.savefig(target, dpi=dpi)
    plt.close(fig)


SHEET_W, SHEET_H = 297.0, 210.0


def sheet_frame(msp, code, name, material, scale_text="SCALE 1:2"):
    """Border and title block, shared by the part and the assembly sheets."""
    W, H = SHEET_W, SHEET_H
    msp.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True)
    msp.add_lwpolyline([(5, 5), (W - 5, 5), (W - 5, H - 5), (5, H - 5)], close=True)

    tb_x, tb_y, tb_w, tb_h = W - 105, 5, 100, 40
    msp.add_lwpolyline([(tb_x, tb_y), (tb_x + tb_w, tb_y),
                        (tb_x + tb_w, tb_y + tb_h), (tb_x, tb_y + tb_h)], close=True)
    for dy in (10, 20, 30):
        msp.add_line((tb_x, tb_y + dy), (tb_x + tb_w, tb_y + dy))
    for dy, text in ((2, "%s        SHEET 1/1" % scale_text),
                     (12, "MATERIAL  %s" % material),
                     (22, name.upper()[:34]),
                     (32, "%s            REV A" % code)):
        msp.add_text(text, height=3.0).set_placement((tb_x + 3, tb_y + dy))
    msp.add_text("OmniaSolutions — OdooPLM demo data", height=2.6).set_placement((10, H - 12))
    return tb_x, tb_y, tb_w, tb_h


def rasterise(doc, msp, pdf_path, png_path):
    """White sheet, black linework — the dark ezdxf default is not a drawing."""
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.config import (BackgroundPolicy, ColorPolicy,
                                             Configuration)
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties

    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")
    context = RenderContext(doc)
    layout_properties = LayoutProperties.from_layout(msp)
    layout_properties.set_colors("#ffffff")
    config = Configuration(color_policy=ColorPolicy.BLACK,
                           background_policy=BackgroundPolicy.WHITE)
    Frontend(context, MatplotlibBackend(ax), config=config).draw_layout(
        msp, finalize=True, layout_properties=layout_properties)
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=100)
    plt.close(fig)


def assembly_sheet(code, name, shape, items, dxf_path, pdf_path, png_path):
    """An assembly sheet with ballooned positions and a parts list.

    This is what the Spare Parts Manual prints: a front elevation of the assembly
    where every component carries the balloon of its position in the bill of
    material, so a reader can go from a number in the parts list to the part on
    the drawing. `items` are dicts with pos, code, qty and the component box in
    model space (x, z, w, h) — the placement the assembly was built from.
    """
    import ezdxf
    from ezdxf.enums import TextEntityAlignment

    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()

    bb = shape.val().BoundingBox()
    span_x = max(bb.xmax - bb.xmin, 1.0)
    span_z = max(bb.zmax - bb.zmin, 1.0)
    view_w, view_h = 150.0, 85.0
    fit = min(view_w / span_x, view_h / span_z)
    # a drawing states a standard scale, not the number that happened to fit
    scale, label = 0.01, "1:100"
    for nice, text in ((1.0, "1:1"), (0.5, "1:2"), (0.4, "1:2.5"), (0.2, "1:5"),
                       (0.1, "1:10"), (0.05, "1:20"), (0.02, "1:50")):
        if nice <= fit:
            scale, label = nice, text
            break
    sheet_frame(msp, code, name, "ASSEMBLY", "SCALE %s" % label)

    ox, oy = 95.0, 135.0
    cx, cz = (bb.xmax + bb.xmin) / 2.0, (bb.zmax + bb.zmin) / 2.0

    def to_sheet(x, z):
        return ox + (x - cx) * scale, oy + (z - cz) * scale

    # the assembly envelope, then every component as a projected box
    x0, y0 = to_sheet(bb.xmin, bb.zmin)
    x1, y1 = to_sheet(bb.xmax, bb.zmax)
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                       dxfattribs={"linetype": "DASHED"})
    msp.add_line((x0 - 6, oy), (x1 + 6, oy), dxfattribs={"linetype": "CENTER"})

    targets = {}
    for item in items:
        px0, py0 = to_sheet(item["x"] - item["w"] / 2.0, item["z"] - item["h"] / 2.0)
        px1, py1 = to_sheet(item["x"] + item["w"] / 2.0, item["z"] + item["h"] / 2.0)
        msp.add_lwpolyline([(px0, py0), (px1, py0), (px1, py1), (px0, py1)], close=True)
        targets[item["pos"]] = ((px0 + px1) / 2.0, (py0 + py1) / 2.0)

    # Balloons down both sides. They are spread over a fixed band rather than over
    # the projected height: a long flat assembly would otherwise stack them on top
    # of each other.
    # side chosen by where the component actually sits, then ordered by height, so
    # the leaders fan out instead of crossing each other
    ordered = sorted(items, key=lambda i: -targets[i["pos"]][1])
    left = [i for i in ordered if targets[i["pos"]][0] <= ox]
    right = [i for i in ordered if targets[i["pos"]][0] > ox]
    band = max(y1 - y0, 11.0 * max(len(left), len(right)))
    top, bottom = oy + band / 2.0, oy - band / 2.0
    for column, xb in ((left, x0 - 20.0), (right, x1 + 20.0)):
        if not column:
            continue
        step = (top - bottom) / (len(column) + 1) if len(column) > 1 else 0
        for n, item in enumerate(column):
            yb = top - (n + 1) * step if step else oy
            msp.add_circle((xb, yb), 4.0)
            msp.add_text(str(item["pos"]), height=3.0).set_placement(
                (xb, yb), align=TextEntityAlignment.MIDDLE_CENTER)
            tx, ty = targets[item["pos"]]
            lead_x = xb + (4.0 if xb < tx else -4.0)
            msp.add_line((lead_x, yb), (tx, ty))
            msp.add_circle((tx, ty), 0.8)

    # parts list, read bottom-up like a real one, sitting on the title block
    tb_x, tb_y, tb_w, tb_h = SHEET_W - 105, 5, 100, 40
    row_h, ty0 = 6.0, tb_y + tb_h
    columns = (0.0, 12.0, 74.0, 100.0)
    for n in range(len(items) + 1):
        y = ty0 + n * row_h
        msp.add_lwpolyline([(tb_x, y), (tb_x + tb_w, y), (tb_x + tb_w, y + row_h),
                            (tb_x, y + row_h)], close=True)
        for dx in columns[1:-1]:
            msp.add_line((tb_x + dx, y), (tb_x + dx, y + row_h))
        if n < len(items):
            item = items[n]
            cells = (str(item["pos"]), item["code"], "%g" % item["qty"])
        else:
            cells = ("POS", "PART NUMBER", "QTY")
        for dx, text in zip(columns[:-1], cells):
            msp.add_text(text, height=2.6).set_placement((tb_x + dx + 2, y + 1.8))

    doc.saveas(dxf_path)
    rasterise(doc, msp, pdf_path, png_path)


def drawing_sheet(code, name, material, shape, dxf_path, pdf_path, png_path):
    """An A4 sheet with two views and a title block — a real 2D PLM document."""
    import ezdxf

    bb = shape.val().BoundingBox()
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    sheet_frame(msp, code, name, material)

    # two orthographic outlines straight from the solid, at 1:2
    scale = 0.5
    for origin, (ax1, ax2) in (((80, 130), (0, 1)), ((205, 110), (0, 2))):
        w = (bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)[ax1] * scale
        h = (bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)[ax2] * scale
        msp.add_lwpolyline([(origin[0] - w / 2, origin[1] - h / 2),
                            (origin[0] + w / 2, origin[1] - h / 2),
                            (origin[0] + w / 2, origin[1] + h / 2),
                            (origin[0] - w / 2, origin[1] + h / 2)], close=True)
        msp.add_line((origin[0] - w / 2 - 6, origin[1]), (origin[0] + w / 2 + 6, origin[1]),
                     dxfattribs={"linetype": "CENTER"})
        msp.add_line((origin[0], origin[1] - h / 2 - 6), (origin[0], origin[1] + h / 2 + 6),
                     dxfattribs={"linetype": "CENTER"})
        dim = msp.add_linear_dim(base=(origin[0], origin[1] - h / 2 - 14),
                                 p1=(origin[0] - w / 2, origin[1] - h / 2),
                                 p2=(origin[0] + w / 2, origin[1] - h / 2), dimstyle="EZDXF")
        dim.render()
    msp.add_text("FRONT", height=3.4).set_placement((66, 96))
    msp.add_text("SIDE", height=3.4).set_placement((193, 60))
    doc.saveas(dxf_path)
    rasterise(doc, msp, pdf_path, png_path)


def markup_canvas(text, cx, cy):
    """fabric.js payload, the format plm_web_3d stores for a 3D markup."""
    return json.dumps({
        "version": "5.1.0",
        "objects": [
            {"type": "circle", "version": "5.1.0", "originX": "left", "originY": "top",
             "left": cx, "top": cy, "width": 110, "height": 110, "fill": "transparent",
             "stroke": "#1f77d0", "strokeWidth": 3, "radius": 55, "startAngle": 0,
             "endAngle": 360, "opacity": 1, "visible": True},
            {"type": "i-text", "version": "5.1.0", "originX": "left", "originY": "top",
             "left": cx - 30, "top": cy + 125, "width": 420, "height": 30,
             "fill": "#000000", "backgroundColor": "#ffffff", "fontFamily": "Helvetica",
             "fontSize": 22, "text": text, "textAlign": "left", "opacity": 1,
             "visible": True},
        ],
    })


# --------------------------------------------------------------------- main ---
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        help="the plm_demo module directory")
    args = parser.parse_args()

    module = args.out
    docs_dir = os.path.join(module, "files", "documents")
    prev_dir = os.path.join(module, "files", "previews")
    imgs_dir = os.path.join(module, "files", "images")
    mark_dir = os.path.join(module, "files", "markups")
    for path in (docs_dir, prev_dir, imgs_dir, mark_dir):
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path)
    work = "/tmp/plm_demo_build"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)

    products, documents, relations, boms = [], [], [], []
    shapes, doc_by_code = {}, {}

    def add_document(fname, doc_type, code, part_xml_id, preview=None, mimetype=None,
                     used_for_spare=False, printout=None):
        with open(os.path.join(docs_dir, fname), "rb") as fh:
            payload = fh.read()
        entry = {
            # the extension is part of the id: a part ships the same name as
            # .3mf and .step, and two documents cannot share an external id
            "xml_id": "doc_%s" % slug(fname),
            "file": fname,
            "name": fname,
            "document_type": doc_type,
            "mimetype": mimetype,
            "engineering_code": code,
            "engineering_revision": 0,
            "engineering_state": "draft",
            "engineering_revision_letter": "A",
            "desc_modify": None,
            "is_library": False,
            "sha1": hashlib.sha1(payload).hexdigest(),
            "preview": preview,
            # the printable version of a 2D document lives in its printout field,
            # not as a document of its own — that is where plm publishes it and
            # where the Spare Parts Manual looks first
            "printout": printout,
            # what plm_spare prints in the Spare Parts Manual: the assembly sheets
            # of the products a spare BOM hangs from, not the single part drawings
            "used_for_spare": bool(used_for_spare),
            "linked_products": [part_xml_id],
        }
        documents.append(entry)
        return entry

    # ---------------------------------------------------------------- parts
    for code, name, builder, material, density, wants_drawing in CATALOG:
        shape = builder()
        shapes[code] = shape
        xml_id = "part_%s" % slug(code)
        volume = shape.val().Volume()

        step = os.path.join(docs_dir, "%s.step" % code)
        stl = os.path.join(work, "%s.stl" % code)
        exporters.export(shape, step)
        exporters.export(shape, stl, tolerance=MESH_TOLERANCE)
        write_3mf(stl, os.path.join(docs_dir, "%s.3mf" % code), name)

        preview_name = "%s.png" % slug(code)
        render(stl, os.path.join(prev_dir, preview_name))
        render(stl, os.path.join(imgs_dir, preview_name), size=(3.0, 2.6), dpi=80)

        products.append({
            "xml_id": xml_id,
            "name": name,
            "default_code": "%s_0" % code,
            "engineering_code": code,
            "engineering_revision": 0,
            "engineering_state": "draft",
            "engineering_revision_letter": "A",
            "engineering_material": material,
            "engineering_surface": None,
            "engineering_treatment": None,
            "type": "consu",
            "is_storable": True,
            "weight": round(volume * density, 4),
            "description": None,
            "image": preview_name,
        })

        # The STEP is the model: the hierarchy, the drawings and the support files
        # all hang from it. The 3MF is what the web viewer renders — an extra file
        # of the model, exactly like the CAD client uploads it (see the ExtraTree
        # branch of plm/controllers/main.py) — and never a parent of anything.
        view_doc = add_document("%s.3mf" % code, "3d", code, xml_id,
                                preview=preview_name, mimetype="model/3mf")
        model_doc = add_document("%s.step" % code, "3d", "%s-STEP" % code, xml_id,
                                 mimetype="application/step")
        doc_by_code[code] = model_doc
        relations.append({"parent": model_doc["xml_id"], "child": view_doc["xml_id"],
                          "link_kind": "ExtraTree"})

        if wants_drawing:
            dxf = os.path.join(docs_dir, "%s-drawing.dxf" % code)
            pdf = os.path.join(docs_dir, "%s-drawing.pdf" % code)
            png = os.path.join(prev_dir, "%s_drawing.png" % slug(code))
            drawing_sheet(code, name, material, shape, dxf, pdf, png)
            dxf_doc = add_document("%s-drawing.dxf" % code, "2d", "%s-DRW" % code, xml_id,
                                   preview="%s_drawing.png" % slug(code),
                                   mimetype="image/vnd.dxf",
                                   printout="%s-drawing.pdf" % code)
            relations.append({"parent": model_doc["xml_id"], "child": dxf_doc["xml_id"],
                              "link_kind": "LyTree"})

    # ----------------------------------------------------------- assemblies
    # placement: (x, y, z) or (x, y, z, degrees about Y) for parts modelled along Z
    # that have to lie along the shaft axis
    placements = {
        "BRG-UNIT-001": {
            "BRG-HSG-001": [(0, 0, 0)],
            "BSH-030-001": [(-12, 0, 34, 90)],
            "SPC-030-001": [(15, 0, 34, 90)],
            "CVR-090-001": [(15, 0, 34, 90)],
            "CAP-052-001": [(-21, 0, 34, 90)],
            "SCR-M6-020": [(0, 27, 60), (0, -27, 60)],
        },
        "LSU-100": {
            "BASE-100": [(0, 0, 0)],
            "BRG-UNIT-001": [(-100, 0, 20), (100, 0, 20)],
            "SHF-020-001": [(-130, 0, 54, 90)],
            "CLP-020-001": [(45, 0, 54, 90), (-45, 0, 54, 90)],
            "SCR-M8-030": [(x, y, 26) for x in (-127, -73, 73, 127) for y in (-27, 27)],
        },
    }
    assembly_shapes = {}
    for code, name, children in ASSEMBLIES:
        asm = cq.Assembly(name=code)
        for child_code, _qty in children:
            shape = assembly_shapes.get(child_code) or shapes.get(child_code)
            for i, place in enumerate(placements[code].get(child_code, [(0, 0, 0)])):
                x, y, z = place[:3]
                angle = place[3] if len(place) > 3 else 0
                location = (cq.Location(cq.Vector(x, y, z), cq.Vector(0, 1, 0), angle)
                            if angle else cq.Location(cq.Vector(x, y, z)))
                asm.add(shape, name="%s_%d" % (child_code, i), loc=location)
        compound = asm.toCompound()
        assembly_shapes[code] = cq.Workplane("XY").newObject([compound])

        xml_id = "part_%s" % slug(code)
        step = os.path.join(docs_dir, "%s.step" % code)
        stl = os.path.join(work, "%s.stl" % code)
        exporters.export(assembly_shapes[code], step)
        exporters.export(assembly_shapes[code], stl, tolerance=MESH_TOLERANCE * 2.5)
        write_3mf(stl, os.path.join(docs_dir, "%s.3mf" % code), name)
        preview_name = "%s.png" % slug(code)
        render(stl, os.path.join(prev_dir, preview_name), size=(5.4, 4.4), dpi=120)
        render(stl, os.path.join(imgs_dir, preview_name), size=(3.2, 2.8), dpi=80)

        products.append({
            "xml_id": xml_id, "name": name, "default_code": "%s_0" % code,
            "engineering_code": code, "engineering_revision": 0,
            "engineering_state": "draft", "engineering_revision_letter": "A",
            "engineering_material": None, "engineering_surface": None,
            "engineering_treatment": None, "type": "consu", "is_storable": True,
            "weight": round(compound.Volume() * STEEL, 4), "description": None,
            "image": preview_name,
        })
        view_doc = add_document("%s.3mf" % code, "3d", code, xml_id,
                                preview=preview_name, mimetype="model/3mf")
        model_doc = add_document("%s.step" % code, "3d", "%s-STEP" % code, xml_id,
                                 mimetype="application/step")
        doc_by_code[code] = model_doc
        relations.append({"parent": model_doc["xml_id"], "child": view_doc["xml_id"],
                          "link_kind": "ExtraTree"})
        # the hierarchy runs model to model, never through the viewer files
        for child_code, _qty in children:
            child_doc = doc_by_code.get(child_code)
            if child_doc:
                relations.append({"parent": model_doc["xml_id"],
                                  "child": child_doc["xml_id"], "link_kind": "HiTree"})

        if code in ASSEMBLY_DRAWINGS:
            items = []
            for i, (child_code, qty) in enumerate(children):
                place = placements[code].get(child_code, [(0, 0, 0)])[0]
                child_shape = assembly_shapes.get(child_code) or shapes.get(child_code)
                cbb = child_shape.val().BoundingBox()
                mx = (cbb.xmax + cbb.xmin) / 2.0
                mz = (cbb.zmax + cbb.zmin) / 2.0
                w, h = cbb.xmax - cbb.xmin, cbb.zmax - cbb.zmin
                if len(place) > 3 and place[3]:
                    # laid down about Y: the local Z becomes the sheet's X
                    w, h = h, w
                    mx, mz = mz, -mx
                items.append({"pos": i + 1, "code": child_code, "qty": float(qty),
                              "x": place[0] + mx, "z": place[2] + mz, "w": w, "h": h})

            dxf = os.path.join(docs_dir, "%s-drawing.dxf" % code)
            pdf = os.path.join(docs_dir, "%s-drawing.pdf" % code)
            png = os.path.join(prev_dir, "%s_drawing.png" % slug(code))
            assembly_sheet(code, name, assembly_shapes[code], items, dxf, pdf, png)
            dxf_doc = add_document("%s-drawing.dxf" % code, "2d", "%s-DRW" % code, xml_id,
                                   preview="%s_drawing.png" % slug(code),
                                   mimetype="image/vnd.dxf", used_for_spare=True,
                                   printout="%s-drawing.pdf" % code)
            relations.append({"parent": model_doc["xml_id"], "child": dxf_doc["xml_id"],
                              "link_kind": "LyTree"})

        boms.append({
            "xml_id": "bom_normal_%s" % slug(code), "code": None, "type": "normal",
            "product": xml_id, "product_qty": 1.0,
            "lines": [{"product": "part_%s" % slug(child), "qty": float(qty),
                       "sequence": (i + 1) * 10}
                      for i, (child, qty) in enumerate(children)],
        })
        if code == "BRG-UNIT-001":
            boms.append({
                "xml_id": "bom_spare_%s" % slug(code), "code": None, "type": "spbom",
                "product": xml_id, "product_qty": 1.0,
                "lines": [{"product": "part_%s" % slug(child), "qty": float(qty),
                           "sequence": (i + 1) * 10}
                          for i, (child, qty) in enumerate(children) if child in SPARES],
            })

    # -------------------------------------------------------------- markups
    top_doc = doc_by_code["LSU-100"]
    base_image = "markup_base.png"
    shutil.copyfile(os.path.join(prev_dir, "%s.png" % slug("LSU-100")),
                    os.path.join(mark_dir, base_image))
    markups = [
        {"xml_id": "markup_clearance", "document": top_doc["xml_id"],
         "comment": "Check the clearance between the clamp ring and the bearing cover",
         "filename": "LSU-100.png", "canvas_data": markup_canvas(
             "Check the clearance between the clamp ring and the bearing cover", 300, 210),
         "base_image": base_image, "message_date": None},
        {"xml_id": "markup_keyway", "document": top_doc["xml_id"],
         "comment": "Keyway orientation to be confirmed with the drive supplier",
         "filename": "LSU-100.png", "canvas_data": markup_canvas(
             "Keyway orientation to be confirmed with the drive supplier", 470, 150),
         "base_image": base_image, "message_date": None},
    ]

    dataset = {
        "source": {"generator": "tools/generate_demo_geometry.py",
                   "product": "Linear shaft support unit (LSU-100)",
                   "license": "AGPL-3.0-or-later, geometry by OmniaSolutions"},
        "products": products,
        "boms": boms,
        "documents": documents,
        "document_relations": relations,
        "markups": markups,
        "chatter": [],
    }
    target = os.path.join(module, "data", "dataset.json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w") as fh:
        json.dump(dataset, fh, indent=1, sort_keys=True)
        fh.write("\n")

    size = sum(os.path.getsize(os.path.join(d, f))
               for d in (docs_dir, prev_dir, imgs_dir, mark_dir) for f in os.listdir(d))
    print("generated %s" % target)
    print("  products            %d" % len(products))
    print("  boms                %d" % len(boms))
    print("  documents           %d" % len(documents))
    print("  document relations  %d" % len(relations))
    print("  markups             %d" % len(markups))
    print("  payload             %.2f MB" % (size / 1e6))


if __name__ == "__main__":
    main()
