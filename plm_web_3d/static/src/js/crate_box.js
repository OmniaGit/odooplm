// A see-through wooden crate on the bounding box of the selected parts, with
// its three dimensions: how big a packing would be.
//
// The crate is exactly the bounding box: the planks, the frame and the braces
// are drawn on the faces, not built as solids that would make it bigger. Its
// wood is drawn in a canvas, so no image ships with it. It is not one of
// OdooCad.items and takes no ray, so picking, measuring, fitting and the
// display modes never see it.

import * as THREE from '../../lib/three.js/build/three.module.js';
import { CSS2DObject } from '../../lib/three.js/examples/jsm/renderers/CSS2DRenderer.js';

const CRATE_OPACITY = 0.35;
const PLANK_MM = 120;            // width of a plank of the sides
const MAX_TEXTURE_PX = 1024;     // longest side of a face texture
const EDGE_COLOR = 0x4a2d12;

// Small seeded generator: the same crate gets the same wood at every redraw
function random(seed) {
	let a = seed >>> 0;
	return () => {
		a = (a + 0x6D2B79F5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

function woodColor(rnd, lightShift = 0) {
	const hue = 30 + rnd() * 7;
	const sat = 36 + rnd() * 12;
	const light = 50 + rnd() * 10 + lightShift;
	return `hsl(${hue}, ${sat}%, ${light}%)`;
}

// A board from (0, 0) to (length, width) in the current transform, grain along
// its length
function drawBoard(ctx, rnd, length, width, lightShift = 0) {
	ctx.fillStyle = woodColor(rnd, lightShift);
	ctx.fillRect(0, 0, length, width);
	const lines = Math.max(4, Math.round(width / 3));
	for (let i = 0; i < lines; i++) {
		const y0 = rnd() * width;
		const amplitude = rnd() * width * 0.06;
		const waves = 1 + rnd() * 3;
		const phase = rnd() * Math.PI * 2;
		ctx.strokeStyle = `rgba(70, 40, 15, ${0.08 + rnd() * 0.2})`;
		ctx.lineWidth = 0.5 + rnd() * 1.2;
		ctx.beginPath();
		for (let x = 0; x <= length; x += Math.max(4, length / 60)) {
			const y = y0 + amplitude * Math.sin(phase + (x / length) * waves * Math.PI * 2);
			if (x === 0) ctx.moveTo(x, y);
			else ctx.lineTo(x, y);
		}
		ctx.stroke();
	}
	// a knot or two
	const knots = rnd() < 0.6 ? 1 + Math.floor(rnd() * 2) : 0;
	for (let i = 0; i < knots; i++) {
		const kx = rnd() * length;
		const ky = width * (0.25 + rnd() * 0.5);
		const r = width * (0.08 + rnd() * 0.1);
		for (let ring = 3; ring > 0; ring--) {
			ctx.strokeStyle = `rgba(80, 45, 15, ${0.15 * ring})`;
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.ellipse(kx, ky, r * ring * 0.9, r * ring * 0.45, 0, 0, Math.PI * 2);
			ctx.stroke();
		}
	}
	// the gap between two boards
	ctx.strokeStyle = 'rgba(45, 25, 8, 0.9)';
	ctx.lineWidth = Math.max(1.5, width * 0.03);
	ctx.strokeRect(0, 0, length, width);
}

function drawNail(ctx, x, y, r) {
	ctx.fillStyle = 'rgba(40, 40, 40, 0.9)';
	ctx.beginPath();
	ctx.arc(x, y, r, 0, Math.PI * 2);
	ctx.fill();
}

// The texture of one face of widthMm x heightMm: horizontal planks, a frame of
// battens and, on the sides, a diagonal brace
function faceTexture(widthMm, heightMm, brace, seed) {
	const scale = MAX_TEXTURE_PX / Math.max(widthMm, heightMm, 1);
	const w = Math.max(64, Math.round(widthMm * scale));
	const h = Math.max(64, Math.round(heightMm * scale));
	const canvas = document.createElement('canvas');
	canvas.width = w;
	canvas.height = h;
	const ctx = canvas.getContext('2d');
	const rnd = random(seed);

	const planks = Math.min(14, Math.max(2, Math.round(heightMm / PLANK_MM)));
	const plankPx = h / planks;
	for (let i = 0; i < planks; i++) {
		ctx.save();
		ctx.translate(0, i * plankPx);
		drawBoard(ctx, rnd, w, plankPx);
		ctx.restore();
	}

	const batten = Math.max(6, Math.min(w, h) * 0.09);
	const boards = [
		[0, 0, w, batten, 0],                    // top
		[0, h - batten, w, batten, 0],           // bottom
		[batten, batten, h - 2 * batten, batten, Math.PI / 2],  // left
		[w, batten, h - 2 * batten, batten, Math.PI / 2],       // right
	];
	for (const [x, y, length, width, angle] of boards) {
		ctx.save();
		ctx.translate(x, y);
		ctx.rotate(angle);
		drawBoard(ctx, rnd, length, width, -10);
		ctx.restore();
	}
	if (brace && w > 4 * batten && h > 4 * batten) {
		const x0 = batten, y0 = h - batten, x1 = w - batten, y1 = batten;
		ctx.save();
		ctx.beginPath();
		ctx.rect(batten, batten, w - 2 * batten, h - 2 * batten);
		ctx.clip();
		ctx.translate(x0, y0);
		ctx.rotate(Math.atan2(y1 - y0, x1 - x0));
		drawBoard(ctx, rnd, Math.hypot(x1 - x0, y1 - y0), batten * 0.9, -6);
		ctx.restore();
	}
	const r = Math.max(1.5, batten * 0.08);
	for (const [x, y] of [[batten / 2, batten / 2], [w - batten / 2, batten / 2],
		[batten / 2, h - batten / 2], [w - batten / 2, h - batten / 2]]) {
		drawNail(ctx, x - r * 2, y, r);
		drawNail(ctx, x + r * 2, y, r);
	}
	const texture = new THREE.CanvasTexture(canvas);
	texture.anisotropy = 4;
	// As the backgrounds do: the canvas colours are sRGB
	texture.encoding = THREE.sRGBEncoding;
	return texture;
}

function dimensionLabel(text, position) {
	const div = document.createElement('div');
	div.className = 'crate_dimension';
	div.textContent = text;
	const label = new CSS2DObject(div);
	label.position.copy(position);
	return label;
}

function formatMm(value) {
	return `${value.toFixed(1)} mm`;
}

// The crate of box (a THREE.Box3), as a group to add to the scene; null for an
// empty box
export function buildCrate(box) {
	if (box.isEmpty()) return null;
	const size = box.getSize(new THREE.Vector3());
	const center = box.getCenter(new THREE.Vector3());
	// A flat part still gets a crate one can see
	const minSide = Math.max(size.x, size.y, size.z) * 0.002 || 0.01;
	const sx = Math.max(size.x, minSide);
	const sy = Math.max(size.y, minSide);
	const sz = Math.max(size.z, minSide);

	// BoxGeometry faces: +x, -x, +y, -y, +z, -z; u runs along the first size
	// named, v along the second
	const faces = [
		[sz, sy, true], [sz, sy, true],
		[sx, sz, false], [sx, sz, false],
		[sx, sy, true], [sx, sy, true],
	];
	const materials = faces.map(([w, h, brace], i) => new THREE.MeshStandardMaterial({
		map: faceTexture(w, h, brace, 1234 + i * 97),
		transparent: true,
		opacity: CRATE_OPACITY,
		depthWrite: false,
		side: THREE.DoubleSide,
		roughness: 1,
		metalness: 0,
	}));
	const geometry = new THREE.BoxGeometry(sx, sy, sz);
	const crate = new THREE.Group();
	crate.name = '__crate_box__';
	const mesh = new THREE.Mesh(geometry, materials);
	mesh.renderOrder = 10;
	crate.add(mesh);
	const edges = new THREE.LineSegments(
		new THREE.EdgesGeometry(geometry),
		new THREE.LineBasicMaterial({ color: EDGE_COLOR }),
	);
	crate.add(edges);

	// Each dimension on an edge of its own, a little off the crate, so the
	// three labels do not pile up on one corner
	const half = new THREE.Vector3(sx / 2, sy / 2, sz / 2);
	const m = Math.max(sx, sy, sz) * 0.05;
	crate.add(dimensionLabel(`X ${formatMm(size.x)}`, new THREE.Vector3(0, -half.y - m, half.z + m)));
	crate.add(dimensionLabel(`Y ${formatMm(size.y)}`, new THREE.Vector3(-half.x - m, 0, half.z + m)));
	crate.add(dimensionLabel(`Z ${formatMm(size.z)}`, new THREE.Vector3(half.x + m, -half.y - m, 0)));
	crate.position.copy(center);
	crate.userData.size = size.clone();
	crate.traverse((child) => { child.raycast = () => { }; });
	return crate;
}

export function disposeCrate(crate) {
	if (!crate) return;
	crate.parent?.remove(crate);
	crate.traverse((child) => {
		if (child.isCSS2DObject) child.element.remove();
		child.geometry?.dispose();
		const materials = Array.isArray(child.material) ? child.material : [child.material];
		for (const material of materials) {
			if (!material) continue;
			material.map?.dispose();
			material.dispose();
		}
	});
}
