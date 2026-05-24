#!/usr/bin/env python3
"""
step_tree_viewer.py — Load a STEP file and render its full assembly tree as a
self-contained interactive HTML page.  Each node shows all available properties:
instance name, clean name, type, color, location, shape analysis (volume,
surface area, bounding box, centre of mass), depth, child count, and collision
/ duplicate-clean-name flags.

The tree-walking logic mirrors _build_step_json_tree from
plm_automated_convertion/models/ir_attachment.py, and _import_step_preserve_names
is taken verbatim from the same module (it has no Odoo dependencies).

Usage
-----
    /media/OneTDisk/virtual_envs/OdooV19/bin/python3 step_tree_viewer.py FILE.step [OUT.html]

    If OUT.html is omitted the HTML is written next to the input file (.html).
"""

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

# ── OCP / CadQuery imports (same block as plm_automated_convertion) ──────────
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
from cadquery.occ_impl.assembly import Color as CQColor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
_logger = logging.getLogger(__name__)


# ── _import_step_preserve_names — copied verbatim from plm_automated_convertion
#    (no Odoo dependency; only OCP + CadQuery) ─────────────────────────────────

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

            inst_name = (f"{_get_name(ref_label) or _get_name(comp_label)}:{i}")
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


# ── Property extraction helpers ───────────────────────────────────────────────

def _color_info(cq_color):
    """Return dict with hex, rgba from a cadquery Color (or None)."""
    if cq_color is None:
        return None
    try:
        r, g, b, a = cq_color.toTuple()
        ri, gi, bi = (min(255, max(0, int(v * 255))) for v in (r, g, b))
        return {
            "hex": f"#{ri:02x}{gi:02x}{bi:02x}",
            "r": round(r, 4), "g": round(g, 4),
            "b": round(b, 4), "a": round(a, 4),
        }
    except Exception:
        return None


def _location_info(cq_loc):
    """Return dict with translation and rotation from a cadquery Location."""
    try:
        (tx, ty, tz), (rx, ry, rz) = cq_loc.toTuple()
        return {
            "translation": {"x": round(tx, 4), "y": round(ty, 4), "z": round(tz, 4)},
            "rotation_deg": {"rx": round(rx, 4), "ry": round(ry, 4), "rz": round(rz, 4)},
            "is_identity": (tx == ty == tz == rx == ry == rz == 0.0),
        }
    except Exception as e:
        return {"error": str(e)}


def _shape_info(cq_obj):
    """Return dict with shape type, volume, area, bbox, CoM from a CQ shape."""
    if cq_obj is None:
        return {}
    result = {}
    try:
        result["shape_type"] = cq_obj.ShapeType()
    except Exception:
        pass
    try:
        result["volume_mm3"] = round(cq_obj.Volume(), 4)
    except Exception:
        pass
    try:
        result["surface_area_mm2"] = round(cq_obj.Area(), 4)
    except Exception:
        pass
    try:
        bb = cq_obj.BoundingBox()
        result["bbox"] = {
            "xmin": round(bb.xmin, 4), "ymin": round(bb.ymin, 4), "zmin": round(bb.zmin, 4),
            "xmax": round(bb.xmax, 4), "ymax": round(bb.ymax, 4), "zmax": round(bb.zmax, 4),
            "dx": round(bb.xmax - bb.xmin, 4),
            "dy": round(bb.ymax - bb.ymin, 4),
            "dz": round(bb.zmax - bb.zmin, 4),
        }
    except Exception:
        pass
    try:
        com = cq_obj.centerOfMass(cq_obj)
        result["center_of_mass"] = {
            "x": round(com.x, 4), "y": round(com.y, 4), "z": round(com.z, 4),
        }
    except Exception:
        pass
    try:
        result["faces"] = len(cq_obj.Faces())
        result["edges"] = len(cq_obj.Edges())
        result["vertices"] = len(cq_obj.Vertices())
        result["solids"] = len(cq_obj.Solids())
    except Exception:
        pass
    return result


# ── Tree builder — mirrors _build_step_json_tree logic ───────────────────────

_node_counter = 0


def _build_viewer_tree(assembly: cq.Assembly, depth: int = 0,
                       parent_name: str = "", child_index: int = 0,
                       ancestor_codes: frozenset = frozenset()) -> dict:
    """Recursively build a property-rich dict tree from a cq.Assembly node.

    Name-cleaning and deduplication rules mirror _build_step_json_tree so the
    viewer reflects exactly what BOM recovery would produce.
    """
    global _node_counter
    _node_counter += 1
    node_id = _node_counter

    # ── clean name (same logic as _build_step_json_tree) ─────────────────────
    raw_name = assembly.name or ""
    clean_name = raw_name.rsplit(":", 1)[0] if ":" in raw_name else raw_name
    if not clean_name:
        if depth == 0:
            clean_name = raw_name or "root"
        else:
            clean_name = f"{parent_name}_{child_index}"

    # ── properties ───────────────────────────────────────────────────────────
    color = _color_info(assembly.color)
    loc   = _location_info(assembly.loc)
    shape = _shape_info(assembly.obj)

    is_assembly = bool(assembly.children)
    node_type   = "Assembly" if is_assembly else "Part"

    # Extract instance index from the raw name (:N suffix)
    inst_idx = None
    if ":" in raw_name:
        try:
            inst_idx = int(raw_name.rsplit(":", 1)[1].split("_")[0])
        except ValueError:
            pass

    node = {
        "id":            node_id,
        "inst_name":     raw_name,
        "clean_name":    clean_name,
        "node_type":     node_type,
        "depth":         depth,
        "inst_index":    inst_idx,
        "material":      assembly.material or None,
        "color":         color,
        "location":      loc,
        "shape":         shape,
        "children":      [],
    }

    # ── deduplicate children — same logic as _build_step_json_tree ────────────
    blocked = ancestor_codes | {clean_name}
    child_info: dict = {}
    unnamed_idx = 0

    for child in assembly.children:
        child_raw   = child.name or ""
        child_clean = child_raw.rsplit(":", 1)[0] if ":" in child_raw else child_raw

        if not child_clean or child_clean in blocked:
            unnamed_idx += 1
            child_info[f"__unnamed_{unnamed_idx}"] = {
                "node": child, "qty": 1, "unnamed_idx": unnamed_idx,
            }
        elif child_clean not in child_info:
            child_info[child_clean] = {"node": child, "qty": 1}
        else:
            child_info[child_clean]["qty"] += 1

    for info in child_info.values():
        child_tree = _build_viewer_tree(
            info["node"],
            depth        = depth + 1,
            parent_name  = clean_name,
            child_index  = info.get("unnamed_idx", 0),
            ancestor_codes = blocked,
        )
        child_tree["qty_in_bom"] = info["qty"]
        node["children"].append(child_tree)

    node["child_count"] = len(node["children"])
    return node


def _annotate_flags(node: dict, all_cleans: list, ancestor_cleans: frozenset = frozenset()):
    """Walk tree and set is_duplicate / is_self_ref_collision / would_be_renamed."""
    clean = node["clean_name"]
    node["is_self_ref_collision"] = clean in ancestor_cleans
    new_ancestors = ancestor_cleans | {clean}
    for child in node["children"]:
        _annotate_flags(child, all_cleans, new_ancestors)


def _collect_cleans(node: dict, out: list):
    out.append(node["clean_name"])
    for child in node["children"]:
        _collect_cleans(child, out)


# ── HTML template — Odoo color schema ────────────────────────────────────────
# Colors sourced from Odoo 19 Community SCSS:
#   brand primary  #71639e  ($o-community-color)
#   grays          $o-gray-100…900
#   success/warning/danger  Bootstrap defaults kept by Odoo

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>STEP Tree &#8212; {filename}</title>
<style>
/* ── Odoo-derived tokens ─────────────────────────────────────── */
:root{{
  --brand:       #71639e;   /* $o-community-color  */
  --brand-dark:  #5a4f80;   /* darken 10%          */
  --brand-light: #ede9f6;   /* tint 90%            */
  --teal:        #17a2b8;   /* $info               */
  --teal-light:  #d1ecf1;
  --success:     #28a745;
  --success-bg:  #d4edda;
  --warning:     #856404;
  --warning-bg:  #fff3cd;
  --danger:      #dc3545;
  --danger-bg:   #f8d7da;
  --gray-100:    #f8f9fa;
  --gray-200:    #e9ecef;
  --gray-300:    #dee2e6;
  --gray-400:    #ced4da;
  --gray-500:    #adb5bd;
  --gray-600:    #6c757d;
  --gray-700:    #495057;
  --gray-800:    #343a40;
  --gray-900:    #212529;
  --white:       #ffffff;
}}
/* ── Reset / base ────────────────────────────────────────────── */
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  font-size:13px;
  color:var(--gray-900);
  background:var(--gray-100);
  height:100vh;
  display:flex;
  flex-direction:column;
  overflow:hidden;
}}
/* ── Top bar (Odoo navbar style) ─────────────────────────────── */
#hdr{{
  background:var(--brand);
  padding:0 16px;
  height:44px;
  display:flex;
  align-items:center;
  gap:10px;
  flex-shrink:0;
  box-shadow:0 1px 4px rgba(0,0,0,.25);
}}
#hdr h1{{
  font-size:14px;
  font-weight:700;
  color:var(--white);
  white-space:nowrap;
  letter-spacing:.2px;
}}
#hdr .sep{{width:1px;height:20px;background:rgba(255,255,255,.25);margin:0 4px}}
.hbadge{{
  font-size:11px;
  padding:2px 9px;
  border-radius:10px;
  background:rgba(255,255,255,.18);
  color:var(--white);
  white-space:nowrap;
  font-weight:500;
}}
.hbadge.warn{{background:rgba(255,193,7,.35)}}
.hbadge.danger{{background:rgba(220,53,69,.45)}}
/* ── Two-panel layout ────────────────────────────────────────── */
#wrap{{display:flex;flex:1;overflow:hidden}}
/* ── Tree panel ──────────────────────────────────────────────── */
#tree-panel{{
  width:400px;
  min-width:240px;
  display:flex;
  flex-direction:column;
  background:var(--white);
  border-right:1px solid var(--gray-300);
}}
#search-wrap{{
  padding:8px 10px;
  border-bottom:1px solid var(--gray-200);
  flex-shrink:0;
}}
#search{{
  width:100%;
  padding:5px 10px;
  border:1px solid var(--gray-300);
  border-radius:4px;
  font-size:12px;
  color:var(--gray-800);
  background:var(--white);
  outline:none;
  transition:border-color .15s;
}}
#search:focus{{border-color:var(--brand)}}
#tree-scroll{{overflow-y:auto;flex:1;padding:6px 8px}}
/* ── Tree nodes ──────────────────────────────────────────────── */
.n{{margin:1px 0}}
.nh{{
  display:flex;
  align-items:center;
  gap:5px;
  padding:4px 6px;
  border-radius:4px;
  cursor:pointer;
  user-select:none;
  transition:background .12s;
}}
.nh:hover{{background:var(--gray-100)}}
.nh.sel{{
  background:var(--brand);
  color:var(--white);
}}
.nh.sel .nlbl .idx{{color:rgba(255,255,255,.65)}}
.nh.sel .typ{{opacity:.9}}
.tog{{
  width:14px;height:14px;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;font-size:9px;color:var(--gray-500);
}}
.tog.leaf{{color:transparent;pointer-events:none}}
.cdot{{
  width:10px;height:10px;
  border-radius:50%;
  border:1px solid var(--gray-300);
  flex-shrink:0;
}}
/* type badges */
.typ{{
  font-size:10px;padding:1px 5px;
  border-radius:3px;font-weight:700;
  flex-shrink:0;letter-spacing:.2px;
}}
.typ-a{{background:var(--brand-light);color:var(--brand-dark)}}
.typ-p{{background:var(--teal-light);color:#0c7080}}
.typ-c{{background:var(--danger-bg);color:var(--danger)}}
.nlbl{{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--gray-800)}}
.nlbl .idx{{color:var(--gray-500);font-size:10px;margin-left:1px}}
.flag-d{{
  font-size:10px;padding:1px 5px;border-radius:3px;
  background:var(--warning-bg);color:var(--warning);
  font-weight:600;flex-shrink:0;
}}
.nc{{
  margin-left:16px;
  border-left:2px solid var(--gray-200);
  padding-left:5px;
}}
.nc.hide{{display:none}}
/* ── Detail panel ────────────────────────────────────────────── */
#detail{{
  flex:1;overflow-y:auto;
  padding:20px;
  background:var(--gray-100);
}}
#no-sel{{
  color:var(--gray-500);
  text-align:center;
  padding:80px 20px;
  font-size:14px;
}}
#no-sel .ico{{font-size:36px;margin-bottom:10px;opacity:.4}}
h2{{
  color:var(--brand-dark);
  font-size:17px;
  font-weight:700;
  margin-bottom:14px;
  padding-bottom:10px;
  border-bottom:2px solid var(--brand-light);
}}
/* property cards */
.sec{{
  background:var(--white);
  border:1px solid var(--gray-200);
  border-radius:6px;
  margin-bottom:10px;
  overflow:hidden;
}}
.sec h3{{
  background:var(--gray-100);
  border-bottom:1px solid var(--gray-200);
  padding:7px 12px;
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.5px;
  color:var(--gray-600);
}}
.pt{{width:100%;border-collapse:collapse;font-size:12px}}
.pt tr:not(:last-child) td{{border-bottom:1px solid var(--gray-100)}}
.pt td{{padding:5px 12px;vertical-align:top}}
.pt td:first-child{{
  color:var(--gray-600);
  width:44%;
  white-space:nowrap;
  font-weight:500;
}}
.pt td:last-child{{
  color:var(--gray-800);
  font-family:'Courier New',monospace;
  word-break:break-all;
}}
/* color preview */
.cprev{{display:inline-flex;align-items:center;gap:8px}}
.cbox{{
  width:22px;height:22px;
  border-radius:4px;
  border:1px solid var(--gray-300);
  flex-shrink:0;
}}
/* flag banners */
.flag-banner{{
  display:flex;align-items:flex-start;gap:8px;
  padding:9px 12px;border-radius:5px;
  font-size:12px;line-height:1.5;margin-bottom:12px;
}}
.flag-ok{{background:var(--success-bg);color:#155724;border:1px solid #c3e6cb}}
.flag-warn{{background:var(--warning-bg);color:#664d03;border:1px solid #ffecb5}}
.flag-err{{background:var(--danger-bg);color:#721c24;border:1px solid #f5c6cb}}
.flag-ico{{font-size:16px;flex-shrink:0;margin-top:1px}}
</style>
</head>
<body>
<div id="hdr">
  <h1>&#9881;&nbsp; STEP Tree Viewer</h1>
  <div class="sep"></div>
  <span class="hbadge" id="b-file"></span>
  <span class="hbadge" id="b-nodes"></span>
  <span class="hbadge" id="b-unique"></span>
  <span class="hbadge warn" id="b-dups"></span>
  <span class="hbadge danger" id="b-coll"></span>
</div>
<div id="wrap">
  <div id="tree-panel">
    <div id="search-wrap">
      <input id="search" placeholder="&#128269; Filter nodes&#x2026;" oninput="doFilter(this.value)">
    </div>
    <div id="tree-scroll"><div id="tree-root"></div></div>
  </div>
  <div id="detail">
    <div id="no-sel">
      <div class="ico">&#128268;</div>
      Click a node in the tree to inspect its properties
    </div>
    <div id="det-content" style="display:none"></div>
  </div>
</div>
<script>
const ROOT  = {json_root};
const STATS = {json_stats};
const FILE  = {json_file};

document.getElementById('b-file').textContent   = FILE;
document.getElementById('b-nodes').textContent  = STATS.total + ' nodes';
document.getElementById('b-unique').textContent = STATS.unique + ' unique names';
document.getElementById('b-dups').textContent   = STATS.dup_count + ' duplicate names';
document.getElementById('b-coll').textContent   = STATS.coll_count + ' collisions';

let selEl = null;
function e(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}}

function mkTree(node, container){{
  const div = document.createElement('div');
  div.className = 'n';
  div.dataset.id    = node.id;
  div.dataset.clean = (node.clean_name || '').toLowerCase();

  const hdr = document.createElement('div');
  hdr.className = 'nh';

  const tog = document.createElement('span');
  tog.className = 'tog' + (node.children.length ? '' : ' leaf');
  tog.textContent = node.children.length ? '&#9654;' : '&#8729;';
  hdr.appendChild(tog);

  if (node.color && node.color.hex) {{
    const dot = document.createElement('span');
    dot.className = 'cdot';
    dot.style.background = node.color.hex;
    hdr.appendChild(dot);
  }}

  const tb = document.createElement('span');
  if (node.is_self_ref_collision) {{
    tb.className = 'typ typ-c'; tb.textContent = 'COLL';
  }} else if (node.node_type === 'Assembly') {{
    tb.className = 'typ typ-a'; tb.textContent = 'ASM';
  }} else {{
    tb.className = 'typ typ-p'; tb.textContent = 'PART';
  }}
  hdr.appendChild(tb);

  const lbl = document.createElement('span');
  lbl.className = 'nlbl';
  const idx = (node.inst_index !== null && node.inst_index !== undefined)
    ? `<span class="idx">:${{node.inst_index}}</span>` : '';
  lbl.innerHTML = e(node.clean_name) + idx;
  hdr.appendChild(lbl);

  if (STATS.dup_names[node.clean_name] && !node.is_self_ref_collision) {{
    const db = document.createElement('span');
    db.className = 'flag-d';
    db.textContent = '\xd7' + STATS.dup_names[node.clean_name];
    hdr.appendChild(db);
  }}

  hdr.onclick = ev => {{ ev.stopPropagation(); selectNode(hdr, node); }};
  div.appendChild(hdr);

  if (node.children.length) {{
    const cc = document.createElement('div');
    cc.className = 'nc hide';
    node.children.forEach(c => mkTree(c, cc));
    div.appendChild(cc);
    tog.onclick = ev => {{
      ev.stopPropagation();
      const h = cc.classList.toggle('hide');
      tog.innerHTML = h ? '&#9654;' : '&#9660;';
    }};
  }}

  container.appendChild(div);
}}

function selectNode(hdrEl, node) {{
  if (selEl) selEl.classList.remove('sel');
  selEl = hdrEl;
  hdrEl.classList.add('sel');
  showDetail(node);
}}

function showDetail(node) {{
  document.getElementById('no-sel').style.display = 'none';
  const panel = document.getElementById('det-content');
  panel.style.display = 'block';

  let html = `<h2>${{e(node.clean_name)}}</h2>`;

  if (node.is_self_ref_collision) {{
    html += `<div class="flag-banner flag-err">
      <span class="flag-ico">&#9888;</span>
      <span><b>Self-reference collision</b> &#8212; this node has the same clean name as an ancestor.
      BOM recovery renames it to <code>${{e(node.clean_name)}}_N</code> to prevent a circular document relation.</span>
    </div>`;
  }} else if (STATS.dup_names[node.clean_name]) {{
    html += `<div class="flag-banner flag-warn">
      <span class="flag-ico">&#8505;</span>
      <span><b>Duplicate clean name</b> &#8212; appears ${{STATS.dup_names[node.clean_name]}}&#215; in the tree.
      This is the same PLM part used multiple times; quantities are summed in the BOM.</span>
    </div>`;
  }} else {{
    html += `<div class="flag-banner flag-ok">
      <span class="flag-ico">&#10003;</span>
      <span>Unique clean name &#8212; no conflicts detected.</span>
    </div>`;
  }}

  html += sec('Identification', [
    ['Instance name (raw)', node.inst_name],
    ['Clean name',          node.clean_name],
    ['Node type',           node.node_type],
    ['Node ID',             node.id],
    ['Depth',               node.depth],
    ['Instance index (:N)', node.inst_index !== null ? node.inst_index : '&#8212;'],
    ['Direct children',     node.child_count],
    ['Qty in BOM',          node.qty_in_bom !== undefined ? node.qty_in_bom : '&#8212;'],
    ['Material',            node.material || '&#8212;'],
  ]);

  const col = node.color;
  html += sec('Color', col ? [
    ['Hex', `<span class="cprev"><span class="cbox" style="background:${{col.hex}}"></span>${{e(col.hex)}}</span>`],
    ['RGBA (0&#8211;1)', `R=${{col.r}}&nbsp; G=${{col.g}}&nbsp; B=${{col.b}}&nbsp; A=${{col.a}}`],
  ] : [['Color', '&#8212; none / inherited from parent']]);

  const loc = node.location || {{}};
  const locRows = [];
  if (loc.is_identity !== undefined) locRows.push(['Is identity', loc.is_identity ? 'Yes' : 'No']);
  if (loc.translation) {{
    const t = loc.translation;
    locRows.push(['Translation (mm)', `X=${{t.x}}&nbsp; Y=${{t.y}}&nbsp; Z=${{t.z}}`]);
  }}
  if (loc.rotation_deg) {{
    const r = loc.rotation_deg;
    locRows.push(['Rotation (deg)', `Rx=${{r.rx}}&nbsp; Ry=${{r.ry}}&nbsp; Rz=${{r.rz}}`]);
  }}
  if (loc.error) locRows.push(['Error', `<span style="color:var(--danger)">${{e(loc.error)}}</span>`]);
  html += sec('Location / Transformation', locRows);

  const sh = node.shape || {{}};
  if (Object.keys(sh).length) {{
    const rows = [];
    if (sh.shape_type      !== undefined) rows.push(['Shape type',   sh.shape_type]);
    if (sh.volume_mm3      !== undefined) rows.push(['Volume',       sh.volume_mm3 + ' mm&#179;']);
    if (sh.surface_area_mm2!== undefined) rows.push(['Surface area', sh.surface_area_mm2 + ' mm&#178;']);
    if (sh.center_of_mass) {{
      const c = sh.center_of_mass;
      rows.push(['Centre of mass', `X=${{c.x}}&nbsp; Y=${{c.y}}&nbsp; Z=${{c.z}}&nbsp;mm`]);
    }}
    if (sh.bbox) {{
      const b = sh.bbox;
      rows.push(['BBox min',      `X=${{b.xmin}}&nbsp; Y=${{b.ymin}}&nbsp; Z=${{b.zmin}}`]);
      rows.push(['BBox max',      `X=${{b.xmax}}&nbsp; Y=${{b.ymax}}&nbsp; Z=${{b.zmax}}`]);
      rows.push(['BBox size (mm)',`${{b.dx}} &#215; ${{b.dy}} &#215; ${{b.dz}}`]);
    }}
    if (sh.solids   !== undefined) rows.push(['Solids',   sh.solids]);
    if (sh.faces    !== undefined) rows.push(['Faces',    sh.faces]);
    if (sh.edges    !== undefined) rows.push(['Edges',    sh.edges]);
    if (sh.vertices !== undefined) rows.push(['Vertices', sh.vertices]);
    html += sec('Shape Analysis', rows);
  }}

  panel.innerHTML = html;
}}

function sec(title, rows) {{
  const rowHtml = rows.map(([k, v]) =>
    `<tr><td>${{e(k)}}</td><td>${{v}}</td></tr>`
  ).join('');
  return `<div class="sec"><h3>${{e(title)}}</h3><table class="pt">${{rowHtml}}</table></div>`;
}}

function doFilter(q) {{
  q = q.toLowerCase().trim();
  document.querySelectorAll('.n').forEach(el => {{
    el.style.display = (!q || (el.dataset.clean || '').includes(q)) ? '' : 'none';
  }});
}}

mkTree(ROOT, document.getElementById('tree-root'));
const firstTog = document.querySelector('#tree-root > .n > .nh > .tog');
if (firstTog && !firstTog.classList.contains('leaf')) firstTog.click();
</script>
</body>
</html>
"""


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step_file", help="Path to the STEP file")
    parser.add_argument("output", nargs="?", help="Output HTML path (default: <step>.html)")
    args = parser.parse_args()

    step_path = Path(args.step_file).resolve()
    if not step_path.exists():
        _logger.error("File not found: %s", step_path)
        sys.exit(1)

    out_path = Path(args.output).resolve() if args.output else step_path.with_suffix(".html")

    _logger.info("Loading %s …", step_path.name)
    asm = _import_step_preserve_names(str(step_path))

    _logger.info("Building property tree …")
    global _node_counter
    _node_counter = 0
    root = _build_viewer_tree(asm)

    # Annotate flags
    all_cleans: list = []
    _collect_cleans(root, all_cleans)
    clean_counts = Counter(all_cleans)
    _annotate_flags(root, all_cleans)

    # Count collisions
    def _count_collisions(node):
        return int(node["is_self_ref_collision"]) + sum(_count_collisions(c) for c in node["children"])

    stats = {
        "total":     len(all_cleans),
        "unique":    len(set(all_cleans)),
        "dup_names": {k: v for k, v in clean_counts.items() if v > 1},
        "dup_count": sum(1 for v in clean_counts.values() if v > 1),
        "coll_count": _count_collisions(root),
    }

    _logger.info(
        "Tree: %d nodes, %d unique clean names, %d duplicate names, %d collisions",
        stats["total"], stats["unique"], stats["dup_count"], stats["coll_count"],
    )

    html = HTML_TEMPLATE.format(
        filename   = step_path.name,
        json_root  = json.dumps(root,  ensure_ascii=False),
        json_stats = json.dumps(stats, ensure_ascii=False),
        json_file  = json.dumps(step_path.name),
    )

    out_path.write_text(html, encoding="utf-8")
    _logger.info("Written → %s", out_path)


if __name__ == "__main__":
    main()
