// The CAD data of a cad3d JSON (schema odooplm.cad3d, written by
// MultiCad/cad3d_export): which face a click hit, the feature (hole, fillet,
// chamfer) that owns it, and a small popup with what the CAD said of it.
//
// The mesh carries one geometry group per CAD face; userData.plm.faces[i].group
// names the group, features[].face_ids the faces of each feature.

import * as THREE from '../../lib/three.js/build/three.module.js';

const SCHEMA = 'odooplm.cad3d';
const POPUP_ID = 'cad3d_info_popup';

const FEATURE_TYPES = { hole: 'Hole', fillet: 'Fillet', chamfer: 'Chamfer' };
const HOLE_TYPES = {
	simple: 'Simple', counterbore: 'Counterbore', countersink: 'Countersink',
	spotface: 'Spotface', tapped: 'Tapped', counterdrill: 'Counterdrill', tapered: 'Tapered',
};
const SURFACES = {
	plane: 'Plane', cylinder: 'Cylinder', cone: 'Cone', sphere: 'Sphere', torus: 'Torus',
	bspline: 'Free form', other: 'Other',
};

const mm = (v) => `${Number(v).toFixed(2)} mm`;
const deg = (v) => `${Number(v).toFixed(1)}°`;
const yesNo = (v) => (v ? 'Yes' : 'No');

// [param, label, format]: the order the popup shows them in.
const PARAMS = [
	['hole_type', 'Type', (v) => HOLE_TYPES[v] || v],
	['diameter', 'Diameter', (v) => `Ø ${mm(v)}`],
	['through', 'Through', yesNo],
	['depth', 'Depth', mm],
	['thread', 'Thread', String],
	['thread_nominal', 'Thread nominal', String],
	['thread_diameter', 'Thread diameter', mm],
	['thread_depth', 'Thread depth', mm],
	['thread_full_depth', 'Full depth thread', yesNo],
	['cbore_diameter', 'Counterbore Ø', mm],
	['cbore_depth', 'Counterbore depth', mm],
	['csink_diameter', 'Countersink Ø', mm],
	['csink_angle', 'Countersink angle', deg],
	['spotface_diameter', 'Spotface Ø', mm],
	['spotface_depth', 'Spotface depth', mm],
	['standard', 'Standard', String],
	['size', 'Size', String],
	['count', 'Instances', String],
	['radius', 'Radius', mm],
	['distance', 'Distance', mm],
	['distance2', 'Distance 2', mm],
	['angle', 'Angle', deg],
];

function isDebug() {
	const page = document.getElementById('main_3d_web');
	return Boolean(page && page.dataset.debug);
}

function plmData(object) {
	for (let node = object; node; node = node.parent) {
		const plm = node.userData && node.userData.plm;
		if (plm && plm.schema === SCHEMA) return plm;
	}
	return null;
}

/**
 * The CAD face and feature under a raycast hit, or null when the object is
 * not a cad3d export. feature is null for a face no feature owns.
 */
export function featureAtHit(hit) {
	if (!hit || !hit.object) return null;
	const plm = plmData(hit.object);
	const geometry = hit.object.geometry;
	if (!plm || !geometry || hit.faceIndex === undefined || hit.faceIndex === null) return null;
	const start = hit.faceIndex * 3;
	const groups = geometry.groups || [];
	const group = groups.findIndex((g) => start >= g.start && start < g.start + g.count);
	const face = (plm.faces || []).find((f) => f.group === group) || null;
	if (!face) return null;
	const feature = (plm.features || []).find((f) => (f.face_ids || []).includes(face.id)) || null;
	return { plm, face, feature };
}

function row(table, label, value, note) {
	const tr = table.insertRow();
	tr.insertCell().textContent = label;
	const cell = tr.insertCell();
	cell.textContent = value;
	if (note) {
		const mark = document.createElement('span');
		mark.className = 'cad3d_info_note';
		mark.textContent = ' *';
		mark.title = note;
		cell.appendChild(mark);
	}
}

function popupElement() {
	let popup = document.getElementById(POPUP_ID);
	if (popup) return popup;
	popup = document.createElement('div');
	popup.id = POPUP_ID;
	popup.className = 'cad3d_info_popup';
	popup.style.display = 'none';
	// A click inside the popup is not a click on the model behind it.
	popup.addEventListener('pointerdown', (e) => e.stopPropagation());
	popup.addEventListener('pointerup', (e) => e.stopPropagation());
	document.body.appendChild(popup);
	document.addEventListener('keydown', (e) => {
		if (e.key === 'Escape') hideFeatureInfo();
	});
	return popup;
}

export function hideFeatureInfo() {
	const popup = document.getElementById(POPUP_ID);
	if (popup) popup.style.display = 'none';
	leader = null;
	hideLeader();
}

// Leader line: from the clicked point of the model to the popup. The point
// is kept in the clicked object's own coordinates, so it follows the part
// when the camera moves; the popup stays where it opened.

const LEADER_ID = 'cad3d_info_leader';
const SVG_NS = 'http://www.w3.org/2000/svg';
let leader = null;      // { object, local }
let lastView = null;    // { camera, canvas } of the last render

/** The popup follows its header while dragged, inside the window. */
function makeDraggable(popup, handle, exclude) {
	handle.classList.add('cad3d_info_handle');
	handle.addEventListener('pointerdown', (e) => {
		if (e.button !== 0 || exclude.contains(e.target)) return;
		e.preventDefault();
		const startX = e.clientX - popup.offsetLeft;
		const startY = e.clientY - popup.offsetTop;
		handle.setPointerCapture(e.pointerId);
		const move = (ev) => {
			const left = Math.min(Math.max(0, ev.clientX - startX), window.innerWidth - popup.offsetWidth);
			const top = Math.min(Math.max(0, ev.clientY - startY), window.innerHeight - popup.offsetHeight);
			popup.style.left = `${left}px`;
			popup.style.top = `${top}px`;
			if (lastView) updateFeatureLeader(lastView.camera, lastView.canvas);
		};
		const stop = (ev) => {
			handle.releasePointerCapture(ev.pointerId);
			handle.removeEventListener('pointermove', move);
			handle.removeEventListener('pointerup', stop);
			handle.removeEventListener('pointercancel', stop);
		};
		handle.addEventListener('pointermove', move);
		handle.addEventListener('pointerup', stop);
		handle.addEventListener('pointercancel', stop);
	});
}

function leaderElement() {
	let svg = document.getElementById(LEADER_ID);
	if (svg) return svg;
	svg = document.createElementNS(SVG_NS, 'svg');
	svg.id = LEADER_ID;
	svg.setAttribute('class', 'cad3d_info_leader');
	const line = document.createElementNS(SVG_NS, 'line');
	const dot = document.createElementNS(SVG_NS, 'circle');
	dot.setAttribute('r', '4');
	svg.append(line, dot);
	document.body.appendChild(svg);
	return svg;
}

function hideLeader() {
	const svg = document.getElementById(LEADER_ID);
	if (svg) svg.style.display = 'none';
}

function isShown(object) {
	for (let node = object; node; node = node.parent) {
		if (!node.visible) return false;
	}
	return true;
}

/**
 * Redraw the leader for the camera as it is now: call it on every render.
 * Hidden when the point is behind the camera, outside the canvas, under the
 * popup, or its part is hidden.
 */
export function updateFeatureLeader(camera, canvas) {
	lastView = { camera, canvas };
	const popup = document.getElementById(POPUP_ID);
	if (!leader || !popup || popup.style.display === 'none' || !isShown(leader.object)) {
		hideLeader();
		return;
	}
	const ndc = leader.object.localToWorld(leader.local.clone()).project(camera);
	const area = canvas.getBoundingClientRect();
	const x = area.left + (ndc.x + 1) / 2 * area.width;
	const y = area.top + (1 - ndc.y) / 2 * area.height;
	const box = popup.getBoundingClientRect();
	const inside = (px, py, r) => px >= r.left && px <= r.right && py >= r.top && py <= r.bottom;
	if (ndc.z < -1 || ndc.z > 1 || !inside(x, y, area) || inside(x, y, box)) {
		hideLeader();
		return;
	}
	// To the nearest point of the popup's border.
	const tx = Math.min(Math.max(x, box.left), box.right);
	const ty = Math.min(Math.max(y, box.top), box.bottom);
	const svg = leaderElement();
	const [line, dot] = svg.childNodes;
	line.setAttribute('x1', x);
	line.setAttribute('y1', y);
	line.setAttribute('x2', tx);
	line.setAttribute('y2', ty);
	dot.setAttribute('cx', x);
	dot.setAttribute('cy', y);
	svg.style.display = 'block';
}

/**
 * Show what the CAD said of the feature owning the face under hit, at the
 * page position (x, y). Anything else under the click closes the popup.
 * Returns true when the popup is shown.
 */
export function showFeatureInfo(hit, x, y) {
	const found = featureAtHit(hit);
	if (!found) {
		hideFeatureInfo();
		return false;
	}
	const { plm, face, feature } = found;
	const popup = popupElement();
	popup.replaceChildren();

	const header = document.createElement('div');
	header.className = 'cad3d_info_header';
	const title = document.createElement('b');
	title.textContent = feature
		? `${FEATURE_TYPES[feature.type] || feature.type}: ${feature.name}`
		: `Face: ${SURFACES[face.surface] || face.surface || 'Unknown'}`;
	const close = document.createElement('span');
	close.className = 'cad3d_info_close';
	close.textContent = '✖';
	close.addEventListener('click', hideFeatureInfo);
	header.append(title, close);
	makeDraggable(popup, header, close);
	popup.appendChild(header);

	const table = document.createElement('table');
	table.className = 'cad3d_info_table';
	const estimated = new Set((feature && feature.from_geometry) || []);
	let anyEstimated = false;
	if (feature) {
		if (feature.suppressed) row(table, 'Suppressed', 'Yes');
		for (const [key, label, format] of PARAMS) {
			const value = feature.params && feature.params[key];
			if (value === undefined || value === null || value === '') continue;
			const note = estimated.has(key) ? 'Taken from the face geometry, not from the feature' : null;
			anyEstimated = anyEstimated || Boolean(note);
			row(table, label, format(value), note);
		}
	} else {
		const params = face.params || {};
		if (params.radius !== undefined) {
			row(table, face.surface === 'cylinder' ? 'Diameter' : 'Radius',
				face.surface === 'cylinder' ? `Ø ${mm(2 * params.radius)}` : mm(params.radius));
		}
		if (params.major_radius !== undefined) row(table, 'Major radius', mm(params.major_radius));
	}
	if (table.rows.length) popup.appendChild(table);

	const dimensions = feature
		? (plm.dimensions || []).filter((d) => d.feature_id === feature.id)
		: [];
	// The CAD dimensions say little to most users: only in Odoo's debug
	// mode, folded under a caption that opens them.
	if (dimensions.length && isDebug()) {
		const caption = document.createElement('div');
		caption.className = 'cad3d_info_caption cad3d_info_toggle';
		const label = () => `${dimTable.hidden ? '▸' : '▾'} Dimensions (${dimensions.length})`;
		const dimTable = document.createElement('table');
		dimTable.className = 'cad3d_info_table';
		dimTable.hidden = true;
		caption.textContent = label();
		caption.addEventListener('click', () => {
			dimTable.hidden = !dimTable.hidden;
			caption.textContent = label();
			if (lastView) updateFeatureLeader(lastView.camera, lastView.canvas);
		});
		popup.appendChild(caption);
		for (const d of dimensions) {
			const value = d.unit === 'mm' ? mm(d.value) : d.unit === 'deg' ? deg(d.value) : String(d.value);
			row(dimTable, d.name, d.expression ? `${value} (${d.expression})` : value);
		}
		popup.appendChild(dimTable);
	}
	if (anyEstimated) {
		const foot = document.createElement('div');
		foot.className = 'cad3d_info_foot';
		foot.textContent = '* taken from the face geometry';
		popup.appendChild(foot);
	}

	leader = { object: hit.object, local: hit.object.worldToLocal(hit.point.clone()) };
	popup.style.display = 'block';
	// Away from the click, so the leader line shows; to the left when the
	// right has no room, and always inside the window.
	const margin = 12;
	const gap = 80;
	const width = popup.offsetWidth;
	const height = popup.offsetHeight;
	let left = x + gap;
	if (left + width > window.innerWidth - margin) left = x - gap - width;
	const top = y - gap / 2 - height / 2;
	popup.style.left = `${Math.max(margin, Math.min(left, window.innerWidth - width - margin))}px`;
	popup.style.top = `${Math.max(margin, Math.min(top, window.innerHeight - height - margin))}px`;
	return true;
}


// Hole textures: the cylindrical faces of every hole get a machined look,
// fine rings for a drilled hole, a helix for a tapped one. The texture is an
// overlay mesh on the same triangles, so the part keeps its own material
// (colour, transparency) and clicks still reach the part's faces.

const OVERLAY_NAME = '__cad3d_hole_texture__';
const DRILL_PERIOD = 1.0;               // mm of hole length per texture tile
const CYLINDER_TOLERANCE = 0.05;        // |normal . axis| allowed on a cylinder
// ISO coarse pitches, by nominal diameter, for a thread that names none.
const ISO_COARSE = [[1.6, 0.35], [2, 0.4], [2.5, 0.45], [3, 0.5], [4, 0.7], [5, 0.8],
	[6, 1], [8, 1.25], [10, 1.5], [12, 1.75], [16, 2], [20, 2.5], [24, 3], [30, 3.5]];

let textures = null;

function stripeTexture(height, shade) {
	const canvas = document.createElement('canvas');
	canvas.width = 4;
	canvas.height = height;
	const ctx = canvas.getContext('2d');
	for (let y = 0; y < height; y++) {
		const v = Math.round(255 * shade(y / height));
		ctx.fillStyle = `rgb(${v},${v},${v})`;
		ctx.fillRect(0, y, 4, 1);
	}
	const texture = new THREE.CanvasTexture(canvas);
	texture.wrapS = THREE.RepeatWrapping;
	texture.wrapT = THREE.RepeatWrapping;
	return texture;
}

function holeTextures() {
	if (textures) return textures;
	// Drilled: uneven fine rings, as a drill leaves them.
	const rings = Array.from({ length: 128 }, () => 0.72 + 0.28 * Math.random());
	const drill = stripeTexture(128, (t) => rings[Math.floor(t * 128)]);
	// Tapped: one thread per tile, light crest, dark root.
	const thread = stripeTexture(64, (t) => 0.35 + 0.65 * (1 - Math.abs(2 * t - 1)));
	const material = (map) => new THREE.MeshStandardMaterial({
		color: 0xb4b8bd,
		metalness: 0.85,
		roughness: 0.35,
		map,
		bumpMap: map,
		bumpScale: 0.6,
		side: THREE.DoubleSide,
		polygonOffset: true,
		polygonOffsetFactor: -1,
		polygonOffsetUnits: -1,
	});
	textures = { drill: material(drill), thread: material(thread) };
	return textures;
}

/** Thread pitch in mm: from the designation, else ISO coarse by diameter. */
export function threadPitch(params) {
	const text = String(params.thread || params.size || '');
	const metric = text.match(/M\s*\d+(?:[.,]\d+)?\s*[xX×]\s*(\d+(?:[.,]\d+)?)/);
	if (metric) return parseFloat(metric[1].replace(',', '.'));
	// Unified: "1/4-20 UNC", "2-56 UNC", "#10-32": threads per inch after the dash.
	const unified = text.match(/(?:^|\s)#?\d+(?:\/\d+)?\s*-\s*(\d+)\b/);
	if (unified) return 25.4 / parseInt(unified[1], 10);
	const diameter = params.thread_diameter || params.diameter || 6;
	let best = ISO_COARSE[0];
	for (const entry of ISO_COARSE) {
		if (Math.abs(entry[0] - diameter) < Math.abs(best[0] - diameter)) best = entry;
	}
	return best[1];
}

function isTapped(params) {
	return params.hole_type === 'tapped' || Boolean(params.thread) || Boolean(params.thread_diameter);
}

function vertexIndex(geometry, i) {
	return geometry.index ? geometry.index.getX(i) : i;
}

/** The axis of a group whose normals are all perpendicular to one, else null. */
function cylinderAxis(geometry, group) {
	const normal = geometry.attributes.normal;
	const n0 = new THREE.Vector3().fromBufferAttribute(normal, vertexIndex(geometry, group.start));
	const n = new THREE.Vector3();
	const axis = new THREE.Vector3();
	let best = 0;
	for (let i = group.start; i < group.start + group.count; i++) {
		n.fromBufferAttribute(normal, vertexIndex(geometry, i));
		const cross = new THREE.Vector3().crossVectors(n0, n);
		if (cross.lengthSq() > best) {
			best = cross.lengthSq();
			axis.copy(cross);
		}
	}
	if (best < 1e-4) return null;          // a plane
	axis.normalize();
	for (let i = group.start; i < group.start + group.count; i++) {
		n.fromBufferAttribute(normal, vertexIndex(geometry, i));
		if (Math.abs(n.dot(axis)) > CYLINDER_TOLERANCE) return null;     // a cone, a torus...
	}
	return axis;
}

/** Triangles of one cylindrical group, with UVs: u in turns, v along the axis. */
function cylinderTriangles(geometry, group, axis, vOf, out) {
	const position = geometry.attributes.position;
	const normal = geometry.attributes.normal;
	const e1 = new THREE.Vector3(1, 0, 0);
	if (Math.abs(e1.dot(axis)) > 0.9) e1.set(0, 1, 0);
	e1.sub(axis.clone().multiplyScalar(e1.dot(axis))).normalize();
	const e2 = new THREE.Vector3().crossVectors(axis, e1);
	const p = new THREE.Vector3();
	const n = new THREE.Vector3();
	for (let i = group.start; i + 2 < group.start + group.count; i += 3) {
		const corners = [];
		for (let k = 0; k < 3; k++) {
			const vi = vertexIndex(geometry, i + k);
			p.fromBufferAttribute(position, vi);
			n.fromBufferAttribute(normal, vi);
			corners.push({
				p: p.clone(),
				n: n.clone(),
				turns: Math.atan2(n.dot(e2), n.dot(e1)) / (2 * Math.PI),
				along: p.dot(axis),
			});
		}
		// Keep the three angles of a triangle on the same side of the seam.
		for (const c of corners) {
			while (c.turns - corners[0].turns > 0.5) c.turns -= 1;
			while (c.turns - corners[0].turns < -0.5) c.turns += 1;
		}
		for (const c of corners) {
			out.positions.push(c.p.x, c.p.y, c.p.z);
			out.normals.push(c.n.x, c.n.y, c.n.z);
			out.uvs.push(c.turns, vOf(c));
		}
	}
}

/**
 * Lay the hole texture over the cylindrical faces of the holes of every
 * cad3d mesh under root. Call it after the viewer has set its materials.
 */
export function addHoleTextures(root) {
	const meshes = [];
	root.traverse((child) => {
		if (child.isMesh && child.name !== OVERLAY_NAME && plmData(child)) meshes.push(child);
	});
	for (const mesh of meshes) {
		const plm = plmData(mesh);
		const geometry = mesh.geometry;
		if (!geometry.attributes.normal || !geometry.groups) continue;
		const faceGroup = new Map((plm.faces || []).map((f) => [f.id, f.group]));
		const kinds = { drill: { positions: [], normals: [], uvs: [] }, thread: { positions: [], normals: [], uvs: [] } };
		for (const feature of plm.features || []) {
			if (feature.type !== 'hole' || feature.suppressed) continue;
			const params = feature.params || {};
			const tapped = isTapped(params);
			const pitch = tapped ? threadPitch(params) : DRILL_PERIOD;
			const vOf = tapped ? (c) => c.along / pitch + c.turns : (c) => c.along / DRILL_PERIOD;
			for (const faceId of feature.face_ids || []) {
				const group = geometry.groups[faceGroup.get(faceId)];
				if (!group || !group.count) continue;
				const axis = cylinderAxis(geometry, group);
				if (axis) cylinderTriangles(geometry, group, axis, vOf, tapped ? kinds.thread : kinds.drill);
			}
		}
		const materials = holeTextures();
		for (const kind of ['drill', 'thread']) {
			const data = kinds[kind];
			if (!data.positions.length) continue;
			const overlayGeometry = new THREE.BufferGeometry();
			overlayGeometry.setAttribute('position', new THREE.Float32BufferAttribute(data.positions, 3));
			overlayGeometry.setAttribute('normal', new THREE.Float32BufferAttribute(data.normals, 3));
			overlayGeometry.setAttribute('uv', new THREE.Float32BufferAttribute(data.uvs, 2));
			const overlay = new THREE.Mesh(overlayGeometry, materials[kind]);
			overlay.name = OVERLAY_NAME;
			overlay.userData.cad3dHoleTexture = kind;
			overlay.raycast = () => { };     // clicks go to the part's own faces
			mesh.add(overlay);
		}
	}
}
