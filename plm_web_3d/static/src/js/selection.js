// Multiple selection of the parts in the 3D viewer.
//
// Shift+click on a part, or on its row of the tree, adds it to the selection
// or takes it out; Esc empties it. A part is a node of the tree
// (OdooCad.tree_ref_elements), as for the hover highlight.
//
// The hover highlight changes the material colour and puts it back when the
// pointer leaves, so the selection never touches the colour: it shows as a
// thick outline of the CAD edges (SELECTION_EDGES_NAME) and a class on the
// tree row, and the two live side by side. WebGL draws plain lines one pixel
// wide, so the outline is a LineSegments2, whose width is in screen pixels.
// A LineSegments2 is a Mesh: hung under the part, every walk that colours the
// meshes of a part (preselection, C, T, saved colours, display modes) would
// take it too. So the outlines live in a group of their own in the scene, and
// follow their part's place and visibility at every frame.

import * as THREE from '../../lib/three.js/build/three.module.js';
import { LineMaterial } from '../../lib/three.js/examples/jsm/lines/LineMaterial.js';
import { LineSegments2 } from '../../lib/three.js/examples/jsm/lines/LineSegments2.js';
import { LineSegmentsGeometry } from '../../lib/three.js/examples/jsm/lines/LineSegmentsGeometry.js';

const SELECTION_EDGES_NAME = '__selection_edges__';
const SELECTION_COLOR = 0xff8c00;
const SELECTION_WIDTH_PX = 3;
// One material for every outline: its resolution follows the canvas
const outlineMaterial = new LineMaterial({
	color: SELECTION_COLOR,
	linewidth: SELECTION_WIDTH_PX,
});
// Overlays that are not geometry of the part (cad3d_features.js, highlight3D)
const SKIPPED_MESHES = ['__cad3d_hole_texture__'];

const selected = new Set();
// guid -> [[mesh, outline], ...]
const outlines = new Map();
const outlineGroup = new THREE.Group();
outlineGroup.name = '__selection_outlines__';
let resolve = () => null;
let onChange = () => { };

export function initSelection(resolver, changed, scene) {
	resolve = resolver;
	onChange = changed;
	scene.add(outlineGroup);
}

function isShown(object) {
	for (let o = object; o; o = o.parent) {
		if (!o.visible) return false;
	}
	return true;
}

// Before every frame: the canvas size the outline width is measured against,
// and each outline on its part, as the part is placed and shown now
export function updateSelectionOutlines(width, height) {
	outlineMaterial.resolution.set(width, height);
	for (const pairs of outlines.values()) {
		for (const [mesh, outline] of pairs) {
			mesh.updateWorldMatrix(true, false);
			outline.matrix.copy(mesh.matrixWorld);
			outline.matrixWorldNeedsUpdate = true;
			outline.visible = isShown(mesh);
		}
	}
}

export function isSelected(guid) {
	return selected.has(guid);
}

// The selected parts, as their 3D objects
export function selectedObjects() {
	return [...selected].map((guid) => resolve(guid)).filter(Boolean);
}

export function toggleSelection(guid) {
	const obj = resolve(guid);
	if (!obj) return;
	if (selected.has(guid)) {
		selected.delete(guid);
		showSelected(guid, obj, false);
	} else {
		selected.add(guid);
		showSelected(guid, obj, true);
	}
	onChange();
}

// Add the parts to the selection, those already in it kept; one change
export function addToSelection(guids) {
	let added = false;
	for (const guid of guids) {
		const obj = resolve(guid);
		if (!obj || selected.has(guid)) continue;
		selected.add(guid);
		showSelected(guid, obj, true);
		added = true;
	}
	if (added) onChange();
}

// Empty the selection; return true when there was something to empty
export function clearSelection() {
	if (selected.size === 0) return false;
	for (const guid of selected) {
		const obj = resolve(guid);
		if (obj) showSelected(guid, obj, false);
	}
	selected.clear();
	onChange();
	return true;
}

function treeRow(guid) {
	return document.querySelector(`.document_tree_line[webgl_ref_name="${guid}"]`);
}

function showSelected(guid, obj, enable) {
	treeRow(guid)?.classList.toggle('document_tree_line_selected', enable);
	for (const [, outline] of outlines.get(guid) || []) {
		outlineGroup.remove(outline);
		outline.geometry.dispose();
	}
	outlines.delete(guid);
	if (!enable) return;
	const pairs = [];
	obj.traverse((child) => {
		if (!child.isMesh || child.name.startsWith('__') || SKIPPED_MESHES.includes(child.name)) return;
		const cadEdges = new THREE.EdgesGeometry(child.geometry, 30);
		const outline = new LineSegments2(
			new LineSegmentsGeometry().fromEdgesGeometry(cadEdges),
			outlineMaterial,
		);
		cadEdges.dispose();
		outline.name = SELECTION_EDGES_NAME;
		outline.matrixAutoUpdate = false;
		outline.raycast = () => { };
		pairs.push([child, outline]);
	});
	for (const [, outline] of pairs) outlineGroup.add(outline);
	outlines.set(guid, pairs);
}
