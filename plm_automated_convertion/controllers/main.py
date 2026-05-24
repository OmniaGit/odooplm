import json
import logging
import os
from collections import Counter

from odoo import http
from odoo.http import request, Response

from ..models.ir_attachment import _import_step_preserve_names

_logger = logging.getLogger(__name__)

# ── Property helpers ──────────────────────────────────────────────────────────


def _color_info(cq_color):
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
    try:
        (tx, ty, tz), (rx, ry, rz) = cq_loc.toTuple()
        return {
            "translation": {"x": round(tx, 4), "y": round(ty, 4), "z": round(tz, 4)},
            "rotation_deg": {"rx": round(rx, 4), "ry": round(ry, 4), "rz": round(rz, 4)},
            "is_identity": (tx == ty == tz == rx == ry == rz == 0.0),
        }
    except Exception as exc:
        return {"error": str(exc)}


def _shape_info(cq_obj):
    if cq_obj is None:
        return {}
    result = {}
    for key, fn in [
        ("shape_type",       lambda o: o.ShapeType()),
        ("volume_mm3",       lambda o: round(o.Volume(), 4)),
        ("surface_area_mm2", lambda o: round(o.Area(), 4)),
        ("faces",            lambda o: len(o.Faces())),
        ("edges",            lambda o: len(o.Edges())),
        ("vertices",         lambda o: len(o.Vertices())),
        ("solids",           lambda o: len(o.Solids())),
    ]:
        try:
            result[key] = fn(cq_obj)
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
    return result


# ── Tree builder (mirrors _build_step_json_tree naming logic) ─────────────────


def _build_viewer_tree(assembly, depth=0, parent_name="", child_index=0,
                       ancestor_codes=frozenset(), _ctr=None):
    if _ctr is None:
        _ctr = [0]
    _ctr[0] += 1

    raw_name = assembly.name or ""
    clean_name = raw_name.rsplit(":", 1)[0] if ":" in raw_name else raw_name
    if not clean_name:
        clean_name = raw_name if depth == 0 else f"{parent_name}_{child_index}"
    elif depth > 0 and clean_name in ancestor_codes:
        base = child_index or 1
        while f"{parent_name}_{base}" in ancestor_codes:
            base += 1
        clean_name = f"{parent_name}_{base}"

    inst_idx = None
    if ":" in raw_name:
        try:
            inst_idx = int(raw_name.rsplit(":", 1)[1].split("_")[0])
        except ValueError:
            pass

    node = {
        "id":         _ctr[0],
        "inst_name":  raw_name,
        "clean_name": clean_name,
        "node_type":  "Assembly" if assembly.children else "Part",
        "depth":      depth,
        "inst_index": inst_idx,
        "material":   assembly.material or None,
        "color":      _color_info(assembly.color),
        "location":   _location_info(assembly.loc),
        "shape":      _shape_info(assembly.obj),
        "children":   [],
    }

    blocked = ancestor_codes | {clean_name}
    child_info = {}
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
            depth=depth + 1,
            parent_name=clean_name,
            child_index=info.get("unnamed_idx", 0),
            ancestor_codes=blocked,
            _ctr=_ctr,
        )
        child_tree["qty_in_bom"] = info["qty"]
        node["children"].append(child_tree)

    node["child_count"] = len(node["children"])
    return node


def _collect_cleans(node, out):
    out.append(node["clean_name"])
    for child in node["children"]:
        _collect_cleans(child, out)


def _annotate_flags(node, ancestor_cleans=frozenset()):
    node["is_self_ref_collision"] = node["clean_name"] in ancestor_cleans
    new_ancestors = ancestor_cleans | {node["clean_name"]}
    for child in node["children"]:
        _annotate_flags(child, new_ancestors)


def _count_collisions(node):
    return int(node["is_self_ref_collision"]) + sum(_count_collisions(c) for c in node["children"])


# ── HTML template ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>STEP Tree &#8212; {filename}</title>
<style>
:root{{
  --brand:       #71639e;
  --brand-dark:  #5a4f80;
  --brand-light: #ede9f6;
  --teal:        #17a2b8;
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
/* ── Header ──────────────────────────────────────────────── */
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
#hdr h1{{font-size:14px;font-weight:700;color:var(--white);white-space:nowrap;letter-spacing:.2px}}
#hdr .sep{{width:1px;height:20px;background:rgba(255,255,255,.25);margin:0 4px}}
.hbadge{{
  font-size:11px;padding:2px 9px;border-radius:10px;
  background:rgba(255,255,255,.18);color:var(--white);white-space:nowrap;font-weight:500;
}}
.hbadge.warn{{background:rgba(255,193,7,.35)}}
.hbadge.danger{{background:rgba(220,53,69,.45)}}
/* ── Layout ──────────────────────────────────────────────── */
#wrap{{display:flex;flex:1;overflow:hidden}}
/* ── Tree panel ──────────────────────────────────────────── */
#tree-panel{{
  width:400px;min-width:220px;
  display:flex;flex-direction:column;
  background:var(--white);
  border-right:1px solid var(--gray-300);
}}
#tree-top{{
  flex-shrink:0;
  border-bottom:1px solid var(--gray-200);
  padding:7px 10px;
  display:flex;flex-direction:column;gap:5px;
}}
#search{{
  width:100%;padding:5px 10px;
  border:1px solid var(--gray-300);border-radius:4px;
  font-size:12px;color:var(--gray-800);background:var(--white);
  outline:none;transition:border-color .15s;
}}
#search:focus{{border-color:var(--brand)}}
#tree-scroll{{overflow-y:auto;flex:1;padding:6px 8px}}
/* ── Tree nodes ──────────────────────────────────────────── */
.n{{margin:1px 0}}
.nh{{
  display:flex;align-items:center;gap:4px;
  padding:3px 4px;border-radius:4px;
  cursor:pointer;user-select:none;transition:background .12s;
}}
.nh:hover{{background:var(--gray-100)}}
.nh.sel{{background:var(--brand);color:var(--white)}}
.nh.sel .nlbl .idx{{color:rgba(255,255,255,.65)}}
.nh.sel .typ{{opacity:.9}}
.ncb{{
  width:14px;height:14px;flex-shrink:0;
  cursor:pointer;accent-color:var(--brand);margin:0;
}}
.tog{{
  width:14px;height:14px;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;font-size:9px;color:var(--gray-500);
}}
.tog.leaf{{color:transparent;pointer-events:none}}
.cdot{{
  width:9px;height:9px;border-radius:50%;
  border:1px solid var(--gray-300);flex-shrink:0;
}}
.typ{{
  font-size:10px;padding:1px 5px;border-radius:3px;
  font-weight:700;flex-shrink:0;letter-spacing:.2px;
}}
.typ-a{{background:var(--brand-light);color:var(--brand-dark)}}
.typ-p{{background:var(--teal-light);color:#0c7080}}
.typ-c{{background:var(--danger-bg);color:var(--danger)}}
.nlbl{{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--gray-800)}}
.nlbl .idx{{color:var(--gray-500);font-size:10px;margin-left:1px}}
.flag-d{{
  font-size:10px;padding:1px 5px;border-radius:3px;
  background:var(--warning-bg);color:var(--warning);font-weight:600;flex-shrink:0;
}}
.nc{{margin-left:20px;border-left:2px solid var(--gray-200);padding-left:4px}}
.nc.hide{{display:none}}
/* ── Detail panel ────────────────────────────────────────── */
#detail{{
  flex:1;overflow-y:auto;
  padding:20px;
  background:var(--gray-100);
}}
#no-sel{{
  color:var(--gray-500);text-align:center;
  padding:80px 20px;font-size:14px;
}}
#no-sel .ico{{font-size:36px;margin-bottom:10px;opacity:.4}}
h2{{
  color:var(--brand-dark);font-size:17px;font-weight:700;
  margin-bottom:14px;padding-bottom:10px;
  border-bottom:2px solid var(--brand-light);
}}
.sec{{
  background:var(--white);border:1px solid var(--gray-200);
  border-radius:6px;margin-bottom:10px;overflow:hidden;
}}
.sec h3{{
  background:var(--gray-100);border-bottom:1px solid var(--gray-200);
  padding:7px 12px;font-size:11px;font-weight:700;
  text-transform:uppercase;letter-spacing:.5px;color:var(--gray-600);
}}
.pt{{width:100%;border-collapse:collapse;font-size:12px}}
.pt tr:not(:last-child) td{{border-bottom:1px solid var(--gray-100)}}
.pt td{{padding:5px 12px;vertical-align:top}}
.pt td:first-child{{color:var(--gray-600);width:44%;white-space:nowrap;font-weight:500}}
.pt td:last-child{{color:var(--gray-800);font-family:'Courier New',monospace;word-break:break-all}}
.cprev{{display:inline-flex;align-items:center;gap:8px}}
.cbox{{width:22px;height:22px;border-radius:4px;border:1px solid var(--gray-300);flex-shrink:0}}
.flag-banner{{
  display:flex;align-items:flex-start;gap:8px;
  padding:9px 12px;border-radius:5px;font-size:12px;
  line-height:1.5;margin-bottom:12px;
}}
.flag-ok{{background:var(--success-bg);color:#155724;border:1px solid #c3e6cb}}
.flag-warn{{background:var(--warning-bg);color:#664d03;border:1px solid #ffecb5}}
.flag-err{{background:var(--danger-bg);color:#721c24;border:1px solid #f5c6cb}}
.flag-ico{{font-size:16px;flex-shrink:0;margin-top:1px}}
/* ── Action panel ────────────────────────────────────────── */
#action-panel{{
  width:250px;min-width:200px;
  display:flex;flex-direction:column;
  background:var(--white);
  border-left:1px solid var(--gray-300);
  overflow-y:auto;
}}
.ap-hdr{{
  background:var(--brand);color:var(--white);
  font-size:12px;font-weight:700;
  padding:10px 14px;letter-spacing:.3px;
  flex-shrink:0;
}}
.ap-sec{{
  padding:12px 14px;
  border-bottom:1px solid var(--gray-200);
}}
.ap-sec-title{{
  font-size:10px;font-weight:700;
  text-transform:uppercase;letter-spacing:.6px;
  color:var(--gray-500);margin-bottom:8px;
}}
#sel-info{{
  font-size:24px;font-weight:700;
  color:var(--brand);margin-bottom:1px;
}}
#sel-sub{{font-size:11px;color:var(--gray-500)}}
.ap-sel-btns{{display:flex;gap:5px;margin-top:8px}}
.ap-sel-btn{{
  flex:1;padding:4px 0;font-size:11px;cursor:pointer;
  border:1px solid var(--gray-300);border-radius:3px;
  background:var(--gray-100);color:var(--gray-700);
  transition:background .12s;
}}
.ap-sel-btn:hover{{background:var(--gray-200)}}
.ap-opt{{
  display:flex;align-items:flex-start;gap:7px;
  margin-bottom:8px;cursor:pointer;
}}
.ap-opt:last-child{{margin-bottom:0}}
.ap-opt input{{
  width:14px;height:14px;flex-shrink:0;margin-top:2px;
  accent-color:var(--brand);cursor:pointer;
}}
.ap-opt-lbl{{font-size:12px;color:var(--gray-800);line-height:1.4}}
.ap-opt-sub{{font-size:10px;color:var(--gray-500);margin-top:1px}}
#create-bom-btn{{
  width:100%;padding:9px;
  background:var(--brand);color:var(--white);
  border:none;border-radius:4px;
  font-size:13px;font-weight:600;
  cursor:pointer;
  transition:background .15s;
}}
#create-bom-btn:hover{{background:var(--brand-dark)}}
#create-bom-btn:disabled{{background:var(--gray-400);cursor:not-allowed}}
#bom-result{{padding:0 14px 12px}}
.res-ok{{
  padding:10px 12px;border-radius:4px;
  background:var(--success-bg);color:#155724;
  border:1px solid #c3e6cb;font-size:12px;
}}
.res-err{{
  padding:10px 12px;border-radius:4px;
  background:var(--danger-bg);color:#721c24;
  border:1px solid #f5c6cb;font-size:12px;
}}
.res-link{{
  display:block;margin-top:7px;
  font-size:12px;color:var(--brand);font-weight:600;
  text-decoration:none;
}}
.res-link:hover{{text-decoration:underline}}
/* ── Loading overlay ─────────────────────────────────────── */
#loading{{
  position:fixed;inset:0;
  background:rgba(0,0,0,.45);
  display:flex;align-items:center;justify-content:center;
  z-index:9999;
}}
.spin-box{{
  background:var(--white);border-radius:8px;
  padding:24px 32px;
  display:flex;align-items:center;gap:14px;
  box-shadow:0 4px 20px rgba(0,0,0,.2);
}}
.spinner{{
  width:22px;height:22px;
  border:3px solid var(--gray-200);
  border-top-color:var(--brand);
  border-radius:50%;
  animation:spin .7s linear infinite;
}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.spin-lbl{{font-size:13px;color:var(--gray-800);font-weight:500}}
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
    <div id="tree-top">
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
  <div id="action-panel">
    <div class="ap-hdr">&#9998;&nbsp; BOM Creation</div>
    <div class="ap-sec">
      <div class="ap-sec-title">Selection</div>
      <div id="sel-info">0</div>
      <div id="sel-sub">nodes selected</div>
      <div class="ap-sel-btns">
        <button class="ap-sel-btn" onclick="selectAll(true)">Select All</button>
        <button class="ap-sel-btn" onclick="selectAll(false)">Select None</button>
      </div>
    </div>
    <div class="ap-sec">
      <div class="ap-sec-title">Options</div>
      <label class="ap-opt">
        <input type="checkbox" id="opt-split">
        <div>
          <div class="ap-opt-lbl">Split to sub-STEP files</div>
          <div class="ap-opt-sub">Export each node as a child .step attachment</div>
        </div>
      </label>
      <label class="ap-opt">
        <input type="checkbox" id="opt-preview">
        <div>
          <div class="ap-opt-lbl">Generate previews</div>
          <div class="ap-opt-sub">Regenerate PNG thumbnails for affected documents</div>
        </div>
      </label>
    </div>
    <div class="ap-sec">
      <button id="create-bom-btn" onclick="createBom()">
        Create BOM &amp; Products
      </button>
    </div>
    <div id="bom-result"></div>
  </div>
</div>
<div id="loading" style="display:none">
  <div class="spin-box">
    <div class="spinner"></div>
    <div class="spin-lbl">Processing STEP assembly&#x2026;</div>
  </div>
</div>
<script>
const ROOT   = {json_root};
const STATS  = {json_stats};
const FILE   = {json_file};
const ATT_ID = {json_att_id};

document.getElementById('b-file').textContent   = FILE;
document.getElementById('b-nodes').textContent  = STATS.total + ' nodes';
document.getElementById('b-unique').textContent = STATS.unique + ' unique names';
document.getElementById('b-dups').textContent   = STATS.dup_count + ' dup names';
document.getElementById('b-coll').textContent   = STATS.coll_count + ' collisions';

// ── HTML escape ───────────────────────────────────────────────
function e(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// ── Node registry ─────────────────────────────────────────────
const nodeMap = new Map();

function registerTree(node, parentId) {{
  nodeMap.set(node.id, {{node, parentId, cb: null}});
  node.children.forEach(c => registerTree(c, node.id));
}}
registerTree(ROOT, null);

// ── Checkbox cascade ──────────────────────────────────────────
function setCbState(nodeId, checked) {{
  const entry = nodeMap.get(nodeId);
  if (!entry || !entry.cb) return;
  entry.cb.checked = checked;
  entry.cb.indeterminate = false;
  entry.node.children.forEach(c => setCbState(c.id, checked));
}}

function refreshAncestors(nodeId) {{
  const entry = nodeMap.get(nodeId);
  if (!entry || entry.parentId === null) return;
  const pe = nodeMap.get(entry.parentId);
  if (!pe || !pe.cb) return;
  const kids = pe.node.children;
  let checked = 0, indet = 0;
  kids.forEach(c => {{
    const ce = nodeMap.get(c.id);
    if (ce && ce.cb) {{
      if (ce.cb.indeterminate) indet++;
      else if (ce.cb.checked) checked++;
    }}
  }});
  if (indet > 0 || (checked > 0 && checked < kids.length)) {{
    pe.cb.indeterminate = true; pe.cb.checked = false;
  }} else if (checked === kids.length) {{
    pe.cb.indeterminate = false; pe.cb.checked = true;
  }} else {{
    pe.cb.indeterminate = false; pe.cb.checked = false;
  }}
  refreshAncestors(entry.parentId);
}}

function onCbChange(nodeId) {{
  const entry = nodeMap.get(nodeId);
  if (!entry) return;
  const checked = entry.cb.checked;
  entry.node.children.forEach(c => setCbState(c.id, checked));
  refreshAncestors(nodeId);
  updateSelCount();
}}

function selectAll(v) {{
  nodeMap.forEach(entry => {{
    if (entry.cb) {{ entry.cb.checked = v; entry.cb.indeterminate = false; }}
  }});
  updateSelCount();
}}

function updateSelCount() {{
  let n = 0;
  nodeMap.forEach(entry => {{
    if (entry.cb && entry.cb.checked && !entry.cb.indeterminate) n++;
  }});
  document.getElementById('sel-info').textContent = n;
  document.getElementById('sel-sub').textContent  = n === 1 ? 'node selected' : 'nodes selected';
}}

function getSelectedNames() {{
  const names = new Set();
  nodeMap.forEach(entry => {{
    if (entry.cb && entry.cb.checked && !entry.cb.indeterminate)
      names.add(entry.node.clean_name);
  }});
  return [...names];
}}

// ── BOM creation ──────────────────────────────────────────────
async function createBom() {{
  const btn = document.getElementById('create-bom-btn');
  const res = document.getElementById('bom-result');
  const sel = getSelectedNames();
  if (!sel.length) {{
    res.innerHTML = '<div class="res-err">&#9888; Select at least one node.</div>';
    return;
  }}
  btn.disabled = true;
  res.innerHTML = '';
  document.getElementById('loading').style.display = 'flex';
  try {{
    const resp = await fetch(`/plm/step_tree/${{ATT_ID}}/create_bom`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        selected_clean_names: sel,
        split:            document.getElementById('opt-split').checked,
        generate_preview: document.getElementById('opt-preview').checked,
      }})
    }});
    const data = await resp.json();
    document.getElementById('loading').style.display = 'none';
    if (data.status === 'ok') {{
      let html = `<div class="res-ok">&#10003; ${{e(data.message)}}`;
      if (data.bom_url)
        html += `<a class="res-link" href="${{e(data.bom_url)}}" target="_top">&#128196; Open Bill of Materials</a>`;
      html += '</div>';
      res.innerHTML = html;
    }} else {{
      res.innerHTML = `<div class="res-err">&#9888; ${{e(data.message || 'Unknown error')}}</div>`;
    }}
  }} catch (ex) {{
    document.getElementById('loading').style.display = 'none';
    res.innerHTML = `<div class="res-err">&#9888; ${{e(String(ex))}}</div>`;
  }} finally {{
    btn.disabled = false;
  }}
}}

// ── Tree rendering ────────────────────────────────────────────
let selEl = null;

function mkTree(node, container) {{
  const div = document.createElement('div');
  div.className = 'n';
  div.dataset.id    = node.id;
  div.dataset.clean = (node.clean_name || '').toLowerCase();

  const hdr = document.createElement('div');
  hdr.className = 'nh';

  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.className = 'ncb';
  cb.checked = !node.is_self_ref_collision;
  cb.addEventListener('change', ev => {{ ev.stopPropagation(); onCbChange(node.id); }});
  cb.addEventListener('click',  ev => ev.stopPropagation());
  hdr.appendChild(cb);
  const entry = nodeMap.get(node.id);
  if (entry) entry.cb = cb;

  const tog = document.createElement('span');
  tog.className = 'tog' + (node.children.length ? '' : ' leaf');
  tog.innerHTML = node.children.length ? '&#9654;' : '&#8729;';
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

  hdr.onclick = ev => {{
    if (ev.target === cb) return;
    ev.stopPropagation();
    selectNode(hdr, node);
  }};
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
      <span><b>Self-reference collision</b> &#8212; same clean name as an ancestor.
      BOM recovery renames it to <code>${{e(node.clean_name)}}_N</code>.</span>
    </div>`;
  }} else if (STATS.dup_names[node.clean_name]) {{
    html += `<div class="flag-banner flag-warn">
      <span class="flag-ico">&#8505;</span>
      <span><b>Duplicate clean name</b> &#8212; appears ${{STATS.dup_names[node.clean_name]}}&#215;
      in the tree. All instances share one PLM part; quantities are summed in the BOM.</span>
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
    if (sh.shape_type       !== undefined) rows.push(['Shape type',   sh.shape_type]);
    if (sh.volume_mm3       !== undefined) rows.push(['Volume',       sh.volume_mm3 + ' mm&#179;']);
    if (sh.surface_area_mm2 !== undefined) rows.push(['Surface area', sh.surface_area_mm2 + ' mm&#178;']);
    if (sh.center_of_mass) {{
      const c = sh.center_of_mass;
      rows.push(['Centre of mass', `X=${{c.x}}&nbsp; Y=${{c.y}}&nbsp; Z=${{c.z}}&nbsp;mm`]);
    }}
    if (sh.bbox) {{
      const b = sh.bbox;
      rows.push(['BBox min',       `X=${{b.xmin}}&nbsp; Y=${{b.ymin}}&nbsp; Z=${{b.zmin}}`]);
      rows.push(['BBox max',       `X=${{b.xmax}}&nbsp; Y=${{b.ymax}}&nbsp; Z=${{b.zmax}}`]);
      rows.push(['BBox size (mm)', `${{b.dx}} &#215; ${{b.dy}} &#215; ${{b.dz}}`]);
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

// ── Pre-check: propagate unchecked collision nodes upward ────────────────────
// Walk bottom-up (post-order). For every node whose checkbox was set to false
// (collision), refreshAncestors sets the parent to indeterminate/unchecked.
function propagateInitialStates(node) {{
  node.children.forEach(c => propagateInitialStates(c));
  refreshAncestors(node.id);
}}
propagateInitialStates(ROOT);
updateSelCount();

// Show a pre-check banner in the action panel when there are collisions.
if (STATS.coll_count > 0) {{
  document.getElementById('bom-result').innerHTML =
    `<div class="res-err" style="margin-top:12px">` +
    `&#9888; ${{STATS.coll_count}} node${{STATS.coll_count > 1 ? 's have' : ' has'}} ` +
    `a naming collision with an ancestor and ${{STATS.coll_count > 1 ? 'have' : 'has'}} been ` +
    `auto-deselected. Review the <b>COLL</b> nodes in the tree before creating the BOM.</div>`;
}}

const firstTog = document.querySelector('#tree-root > .n > .nh > .tog');
if (firstTog && !firstTog.classList.contains('leaf')) firstTog.click();
</script>
</body>
</html>
"""


# ── Controller ────────────────────────────────────────────────────────────────


class StepTreeController(http.Controller):

    @http.route(
        "/plm/step_tree/<int:attachment_id>",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def step_tree(self, attachment_id, **kwargs):
        attachment = request.env["ir.attachment"].browse(attachment_id)
        if not attachment.exists():
            return Response("Attachment not found", status=404, content_type="text/plain")

        name = (attachment.name or "").lower()
        if not any(ext in name for ext in [".stp", ".step"]):
            return Response("Not a STEP file", status=400, content_type="text/plain")

        store_fname = attachment._full_path(attachment.store_fname)
        if not store_fname or not os.path.exists(store_fname):
            return Response(
                "STEP file not found on disk", status=404, content_type="text/plain"
            )

        try:
            asm = _import_step_preserve_names(store_fname)
        except Exception as exc:
            _logger.exception("step_tree: failed to parse %s", attachment.name)
            return Response(
                f"Error parsing STEP file: {exc}", status=500, content_type="text/plain"
            )

        root = _build_viewer_tree(asm)

        all_cleans: list = []
        _collect_cleans(root, all_cleans)
        clean_counts = Counter(all_cleans)
        _annotate_flags(root)

        stats = {
            "total":     len(all_cleans),
            "unique":    len(set(all_cleans)),
            "dup_names": {k: v for k, v in clean_counts.items() if v > 1},
            "dup_count": sum(1 for v in clean_counts.values() if v > 1),
            "coll_count": _count_collisions(root),
        }

        html = HTML_TEMPLATE.format(
            filename    = attachment.name,
            json_root   = json.dumps(root,  ensure_ascii=False),
            json_stats  = json.dumps(stats, ensure_ascii=False),
            json_file   = json.dumps(attachment.name),
            json_att_id = attachment_id,
        )

        return Response(html, content_type="text/html; charset=utf-8")

    @http.route(
        "/plm/step_tree/<int:attachment_id>/create_bom",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def step_tree_create_bom(self, attachment_id, **kwargs):
        attachment = request.env["ir.attachment"].browse(attachment_id)
        if not attachment.exists():
            return Response(
                json.dumps({"status": "error", "message": "Attachment not found"}),
                content_type="application/json",
                status=404,
            )

        try:
            body = json.loads(request.httprequest.data or b"{}")
        except Exception:
            body = {}

        selected = body.get("selected_clean_names") or None
        split = bool(body.get("split", False))
        generate_preview = bool(body.get("generate_preview", False))

        try:
            with request.env.cr.savepoint():
                attachment.recover_bom_from_step(
                    split=split,
                    generate_preview=generate_preview,
                    selected_clean_names=selected,
                )
            bom_url = None
            origin = attachment.linkedcomponents[:1]
            if origin:
                bom = request.env["mrp.bom"].search(
                    [("product_tmpl_id", "=", origin.product_tmpl_id.id)],
                    limit=1,
                )
                if bom:
                    bom_url = f"/web#model=mrp.bom&id={bom.id}&view_type=form"
            result = {
                "status": "ok",
                "message": "BOM and products created successfully.",
                "bom_url": bom_url,
            }
        except Exception as exc:
            _logger.exception("step_tree_create_bom: failed for attachment %s", attachment_id)
            result = {"status": "error", "message": str(exc)}

        return Response(
            json.dumps(result, ensure_ascii=False),
            content_type="application/json",
        )
