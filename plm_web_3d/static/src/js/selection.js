// Multiple selection of the parts in the 3D viewer.
//
// Shift+click on a part, or on its row of the tree, adds it to the selection
// or takes it out; Esc empties it. A part is a node of the tree
// (OdooCad.tree_ref_elements), as for the hover highlight.
//
// The hover highlight changes the material colour and puts it back when the
// pointer leaves, so the selection never touches the colour: it shows as edges
// of its own (SELECTION_EDGES_NAME) and a class on the tree row, and the two
// live side by side.

import * as THREE from '../../lib/three.js/build/three.module.js';

const SELECTION_EDGES_NAME = '__selection_edges__';
const SELECTION_COLOR = 0xff8c00;
// Overlays that are not geometry of the part (cad3d_features.js, highlight3D)
const SKIPPED_MESHES = ['__cad3d_hole_texture__'];

const selected = new Set();
let resolve = () => null;
let onChange = () => { };

export function initSelection(resolver, changed) {
	resolve = resolver;
	onChange = changed;
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
	const meshes = [];
	obj.traverse((child) => {
		if (child.isMesh && !SKIPPED_MESHES.includes(child.name)) meshes.push(child);
	});
	for (const mesh of meshes) {
		const edges = mesh.getObjectByName(SELECTION_EDGES_NAME);
		if (enable && !edges) {
			const lines = new THREE.LineSegments(
				new THREE.EdgesGeometry(mesh.geometry, 30),
				new THREE.LineBasicMaterial({ color: SELECTION_COLOR }),
			);
			lines.name = SELECTION_EDGES_NAME;
			lines.raycast = () => { };
			mesh.add(lines);
		} else if (!enable && edges) {
			mesh.remove(edges);
			edges.geometry.dispose();
			edges.material.dispose();
		}
	}
}
