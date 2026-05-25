// some of the code here is taken from
// https://github.com/leemun1/three-viewcube
// thanks https://github.com/leemun1

import * as THREE from './lib/three.js/build/three.module.js';
import * as ODOOCAD from './lib/odoocad/odoocad.js';
// controls
import { OrbitControls } from './lib/three.js/examples/jsm/controls/OrbitControls.js';
import { TransformControls } from './lib/three.js/examples/jsm/controls/TransformControls.js';
import Stats from './lib/three.js/examples/jsm/libs/stats.module.js';
import {
	CSS2DRenderer,
	CSS2DObject,
} from './lib/three.js/examples/jsm/renderers/CSS2DRenderer.js'

var debug_3d = false;
let OdooCad;
let cube;
let clicked = false;
const ODOO_COLOR = '#714B67';
const DEBUG_SCENE = true;
var strDownloadMime = "image/octet-stream";

const measurementLabels = {};
const endPoint = {};
const startPoint = {};
const lines = {};
const startSnapTypes = {};
const endSnapTypes = {};
const startArrow = {};
const endArrow = {};
let camera, scene, canvas, renderer, labelRenderer, controls, mouse;
let planeMeshFloar, planeGrid;
let objectAxesHelper;
let raycaster;
let light1, light2, light3, cameraLight, ambientLight;
var srcRefresh = false;
var togleBackgoundV = false;
let drawingLine = false;
let lineId = 0;
let bbox_center = new THREE.Vector3();
const fov = 75;
const near = 0.1;
const far = 1000;
var aspect = 2;  // the canvas default

var mesure_items = [];
var snapDistance = 2;
var sphereHelper;
var sphereHelperDiv;
let ctrlDown = false;
const pointer = new THREE.Vector2();
let zoomWindowActive = false;
let _zoomDragging = false;
let _zoomStartX = 0, _zoomStartY = 0;
let sectionPlaneActive = false;
let sectionPlane = null;
let sectionPlaneMesh = null;
let sectionTransformCtrl = null;
let sectionPlaneMode = 'translate';
let sectionCapPlane = null;
const sectionStencilMeshes = [];
let _lastPointerX = 0, _lastPointerY = 0;
const _recentColors = [];
const _partColors = {};
const _partOpacity = {};
let _partColorsDocId = null;
let last_highlighted_li = null;
let last_highlighted_part = null;
const ODOO_HILIGHT_COLOR = new THREE.Color("#eda3da");

function createSpriteTexture(hexColor) {
	const size = 64;
	const canvas = document.createElement('canvas');
	canvas.width = size;
	canvas.height = size;
	const ctx = canvas.getContext('2d');
	ctx.beginPath();
	ctx.arc(size / 2, size / 2, size / 2 - 2, 0, Math.PI * 2);
	ctx.fillStyle = hexColor;
	ctx.fill();
	ctx.strokeStyle = 'rgba(0,0,0,0.45)';
	ctx.lineWidth = 2;
	ctx.stroke();
	return new THREE.CanvasTexture(canvas);
}

const SNAP_ARROW_COLOR = { vertex: '#ffff88', face: '#88eeff' };

function createArrowSpriteTexture(hexColor) {
	const size = 64;
	const cv = document.createElement('canvas');
	cv.width = size; cv.height = size;
	const ctx = cv.getContext('2d');
	// Outline first (drawn slightly larger, gives contrast on any background)
	ctx.beginPath();
	ctx.moveTo(size - 2, size / 2);
	ctx.lineTo(2, 6);
	ctx.lineTo(2, size - 6);
	ctx.closePath();
	ctx.strokeStyle = 'rgba(0,0,0,0.55)';
	ctx.lineWidth = 4;
	ctx.lineJoin = 'round';
	ctx.stroke();
	// Filled arrow on top
	ctx.beginPath();
	ctx.moveTo(size - 4, size / 2);
	ctx.lineTo(5, 10);
	ctx.lineTo(5, size - 10);
	ctx.closePath();
	ctx.fillStyle = hexColor;
	ctx.fill();
	return new THREE.CanvasTexture(cv);
}

function createArrowSprite(hexColor) {
	const mat = new THREE.SpriteMaterial({
		map: createArrowSpriteTexture(hexColor),
		depthTest: false,
		transparent: true,
		sizeAttenuation: true,
	});
	const sprite = new THREE.Sprite(mat);
	scene.add(sprite);
	return sprite;
}

function createSphereHelper() {
	const material = new THREE.SpriteMaterial({
		map: createSpriteTexture('#ffff00'),
		depthTest: false,
		transparent: true,
	});
	sphereHelper = new THREE.Sprite(material);
	sphereHelper.visible = false;
	scene.add(sphereHelper);
}

function _scaleSpriteToPixels(sprite, pixelSize) {
	const dist = camera.position.distanceTo(sprite.position);
	const vFov = camera.fov * Math.PI / 180;
	const worldPerPx = (2 * dist * Math.tan(vFov / 2)) / renderer.domElement.clientHeight;
	const s = pixelSize * worldPerPx;
	sprite.scale.set(s, s, 1);
}

function openOdooPopup(model, id) {
	window.open(
		`/web#model=${model}&id=${id}&view_type=form`,
		"_blank",
		"width=1200,height=800,resizable=yes,scrollbars=yes,noopener=yes"
	);
}
window.openOdooPopup = openOdooPopup;

function _addRecentColor(hex) {
	const h = hex.toLowerCase();
	const idx = _recentColors.indexOf(h);
	if (idx !== -1) _recentColors.splice(idx, 1);
	_recentColors.unshift(h);
	if (_recentColors.length > 4) _recentColors.length = 4;
}

function _renderRecentColors() {
	const row = document.getElementById('part_color_recents');
	if (!row) return;
	row.innerHTML = '';
	_recentColors.forEach(hex => {
		const btn = document.createElement('button');
		btn.style.cssText = `width:24px;height:24px;background:${hex};border:1px solid #888;border-radius:3px;cursor:pointer;padding:0;flex-shrink:0;`;
		btn.title = hex;
		btn.addEventListener('click', () => {
			const input = document.getElementById('part_color_input');
			if (input && input._guid) {
				input.value = hex;
				input.dispatchEvent(new Event('input'));
			}
		});
		row.appendChild(btn);
	});
	row.style.display = _recentColors.length ? 'flex' : 'none';
}

function _applyPartAppearance(stored) {
	// Support both old flat format {"name":"#hex"} and new {"colors":{...},"opacities":{...}}
	let colorsMap = {};
	let opacityMap = {};
	if (stored && (stored.colors || stored.opacities)) {
		colorsMap = stored.colors || {};
		opacityMap = stored.opacities || {};
	} else {
		colorsMap = stored || {};
	}
	// tree_ref_elements keys are session-random GUIDs; match by stable obj.name
	Object.entries(OdooCad.tree_ref_elements).forEach(([sessionGuid, obj]) => {
		const partName = obj.name;
		if (!partName) return;
		const hex = colorsMap[partName];
		const opacity = opacityMap[partName];
		if (!hex && opacity === undefined) return;
		if (hex) _partColors[partName] = hex;
		if (opacity !== undefined) _partOpacity[partName] = opacity;
		obj.traverse(child => {
			if (!(child instanceof THREE.Mesh && child.material)) return;
			if (hex) {
				child.material.color.setStyle(hex);
				child.material.userData.originalColor = child.material.color.clone();
				child.material.userData.oldColor = child.material.color.clone();
			}
			if (opacity !== undefined) {
				const wasTransparent = child.material.transparent;
				child.material.transparent = opacity < 1.0;
				child.material.opacity = opacity;
				child.material.userData.originalOpacity = opacity;
				if (child.material.transparent !== wasTransparent) {
					child.material.needsUpdate = true;
				}
			}
		});
		if (hex) {
			const treeInput = document.querySelector(`.tree_item_color[webgl_ref_name="${sessionGuid}"]`);
			if (treeInput) treeInput.value = hex;
		}
	});
}

function _savePartColors() {
	const hasColors = Object.keys(_partColors).length > 0;
	const hasOpacity = Object.keys(_partOpacity).length > 0;
	if (!_partColorsDocId || (!hasColors && !hasOpacity)) return;
	const btn = document.getElementById('save_part_colors_btn');
	const payload = { colors: _partColors, opacities: _partOpacity };
	fetch('/plm/part_colors/save', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			jsonrpc: '2.0', method: 'call', id: 1,
			params: { document_id: _partColorsDocId, colors: payload },
		}),
	})
		.then(r => r.json())
		.then(data => {
			if (data.result && data.result.success) {
				if (btn) {
					btn.classList.remove('color-unsaved');
					btn.classList.add('color-save-ok');
					setTimeout(() => btn.classList.remove('color-save-ok'), 1500);
				}
			} else {
				if (btn) {
					btn.classList.add('color-save-err');
					setTimeout(() => btn.classList.remove('color-save-err'), 1500);
				}
			}
		})
		.catch(() => {
			if (btn) {
				btn.classList.add('color-save-err');
				setTimeout(() => btn.classList.remove('color-save-err'), 1500);
			}
		});
}

function _markAppearanceDirty() {
	document.getElementById('save_part_colors_btn')?.classList.add('color-unsaved');
}

function _hidePartColorPicker() {
	const popup = document.getElementById('part_color_popup');
	if (popup) popup.style.display = 'none';
}

function _hidePartTransparencyPicker() {
	const popup = document.getElementById('part_transparency_popup');
	if (popup) popup.style.display = 'none';
}

function _showPartTransparencyPicker(guid) {
	const popup = document.getElementById('part_transparency_popup');
	const slider = document.getElementById('part_transparency_slider');
	const label = document.getElementById('part_transparency_label');
	if (!popup || !slider) return;

	// Read current opacity from first found mesh
	let currentOpacity = 1.0;
	const groupObj = OdooCad.tree_ref_elements[guid];
	if (groupObj) {
		let found = false;
		groupObj.traverse(child => {
			if (!found && child instanceof THREE.Mesh && child.material) {
				currentOpacity = child.material.opacity !== undefined ? child.material.opacity : 1.0;
				found = true;
			}
		});
	}
	slider.value = Math.round(currentOpacity * 100);
	if (label) label.textContent = slider.value + '%';
	slider._guid = guid;

	const pw = 190, ph = 80;
	const vw = window.innerWidth, vh = window.innerHeight;
	let left = _lastPointerX + 14;
	let top = _lastPointerY + 14;
	if (left + pw > vw) left = _lastPointerX - pw - 8;
	if (top + ph > vh) top = _lastPointerY - ph - 8;
	popup.style.left = left + 'px';
	popup.style.top = top + 'px';
	popup.style.display = 'block';
}

function _showPartColorPicker(guid) {
	const popup = document.getElementById('part_color_popup');
	const input = document.getElementById('part_color_input');
	if (!popup || !input) return;

	// Read current color from first found mesh
	let currentHex = '#ffffff';
	const groupObj = OdooCad.tree_ref_elements[guid];
	if (groupObj) {
		let found = false;
		groupObj.traverse(child => {
			if (!found && child instanceof THREE.Mesh && child.material) {
				currentHex = '#' + child.material.color.getHexString();
				found = true;
			}
		});
	}
	input.value = currentHex;
	input._guid = guid;

	// Position near cursor, clamped to viewport
	const pw = 140, ph = 72;
	const vw = window.innerWidth, vh = window.innerHeight;
	let left = _lastPointerX + 14;
	let top = _lastPointerY + 14;
	if (left + pw > vw) left = _lastPointerX - pw - 8;
	if (top + ph > vh) top = _lastPointerY - ph - 8;
	_renderRecentColors();
	popup.style.left = left + 'px';
	popup.style.top = top + 'px';
	popup.style.display = 'block';
}

function _activateMeasure() {
	ctrlDown = true;
	drawingLine = true;
	renderer.domElement.style.cursor = "crosshair";
	document.getElementById("measure_btn_perm")?.classList.add("active");
}

function _removeArrow(sprite) {
	if (!sprite) return;
	scene.remove(sprite);
	sprite.material.map?.dispose();
	sprite.material.dispose();
}

function _deactivateMeasure() {
	ctrlDown = false;
	drawingLine = false;
	renderer.domElement.style.cursor = "pointer";
	document.getElementById("measure_btn_perm")?.classList.remove("active");
	scene.remove(measurementLabels[lineId]);
	scene.remove(startPoint[lineId]);
	scene.remove(endPoint[lineId]);
	scene.remove(lines[lineId]);
	_removeArrow(startArrow[lineId]);
	_removeArrow(endArrow[lineId]);
	delete startArrow[lineId];
	delete endArrow[lineId];
	lineId++;
}

function _activateZoomWindow() {
	zoomWindowActive = true;
	renderer.domElement.style.cursor = "crosshair";
	document.getElementById("zoom_window_btn")?.classList.add("active");
}

function _deactivateZoomWindow() {
	zoomWindowActive = false;
	_zoomDragging = false;
	controls.enabled = true;
	renderer.domElement.style.cursor = "pointer";
	document.getElementById("zoom_window_btn")?.classList.remove("active");
	const rectEl = document.getElementById("zoom_window_rect");
	if (rectEl) rectEl.style.display = "none";
}

function zoomToWindow(canvasX, canvasY, selW, selH) {
	const cw = renderer.domElement.clientWidth;
	const ch = renderer.domElement.clientHeight;

	// NDC centre of the selection rectangle
	const ndcX = (canvasX + selW / 2) / cw * 2 - 1;
	const ndcY = -((canvasY + selH / 2) / ch * 2 - 1);

	// Ray through the selection centre
	const ray = new THREE.Raycaster();
	ray.setFromCamera(new THREE.Vector2(ndcX, ndcY), camera);

	// Find new orbit target: hit scene geometry, else current focal plane
	let newTarget;
	const hits = ray.intersectObjects(OdooCad.items, true);
	if (hits.length > 0) {
		newTarget = hits[0].point.clone();
	} else {
		const focalDist = camera.position.distanceTo(controls.target);
		newTarget = ray.ray.at(focalDist, new THREE.Vector3());
	}

	// Zoom factor: selection fills the viewport
	const zoomFactor = Math.min(cw / selW, ch / selH);
	const currentDist = camera.position.distanceTo(controls.target);
	const newDist = Math.max(currentDist / zoomFactor, 0.01);

	// Move camera along the same look direction at new distance from new target
	const dir = camera.position.clone().sub(controls.target).normalize();
	camera.position.copy(newTarget).addScaledVector(dir, newDist);
	controls.target.copy(newTarget);
	controls.minDistance = 0.01;
	controls.maxDistance = newDist * 10;
	camera.near = newDist / 100;
	camera.far = newDist * 100;
	camera.updateProjectionMatrix();
	controls.update();
	render();
}

function createSectionPlane() {
	// Compute bounding box from loaded scene objects
	const box = new THREE.Box3();
	const refItems = Object.values(OdooCad.tree_ref_elements);
	const targets = refItems.length > 0 ? refItems : OdooCad.items;
	for (const obj of targets) box.expandByObject(obj);
	const center = box.getCenter(new THREE.Vector3());
	const size = box.getSize(new THREE.Vector3());
	const planeSize = Math.max(size.x, size.z) * 1.5 || 100;

	// Horizontal plane at bbox center, normal pointing up (+Y clips below)
	sectionPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -center.y);
	renderer.clippingPlanes = [sectionPlane];

	// Visible plane mesh — PlaneGeometry lies in XY, rotate to XZ (horizontal)
	const geo = new THREE.PlaneGeometry(planeSize, planeSize);
	const mat = new THREE.MeshBasicMaterial({
		color: 0x714B67,
		side: THREE.DoubleSide,
		transparent: true,
		opacity: 0.18,
		depthWrite: false,
	});
	sectionPlaneMesh = new THREE.Mesh(geo, mat);
	sectionPlaneMesh.rotation.x = -Math.PI / 2;
	sectionPlaneMesh.position.copy(center);
	sectionPlaneMesh.add(new THREE.LineSegments(
		new THREE.EdgesGeometry(geo),
		new THREE.LineBasicMaterial({ color: 0x714B67 })
	));
	scene.add(sectionPlaneMesh);

	// TransformControls gizmo
	sectionTransformCtrl = new TransformControls(camera, renderer.domElement);
	sectionTransformCtrl.setMode('translate');
	sectionTransformCtrl.attach(sectionPlaneMesh);
	scene.add(sectionTransformCtrl);

	sectionTransformCtrl.addEventListener('dragging-changed', function (e) {
		controls.enabled = !e.value;
	});
	sectionTransformCtrl.addEventListener('objectChange', _syncSectionPlane);
	sectionTransformCtrl.addEventListener('change', render);

	const modeBtn = document.getElementById('section_plane_mode_btn');
	if (modeBtn) modeBtn.style.display = '';
	createSectionCap();
	render();
}

function _syncSectionPlane() {
	if (!sectionPlaneMesh || !sectionPlane) return;
	sectionPlaneMesh.updateMatrixWorld();
	// PlaneGeometry local normal is (0,0,1); transformDirection gives world-space normal
	const normal = new THREE.Vector3(0, 0, 1).transformDirection(sectionPlaneMesh.matrixWorld);
	const pos = new THREE.Vector3();
	sectionPlaneMesh.getWorldPosition(pos);
	sectionPlane.setFromNormalAndCoplanarPoint(normal, pos);
	updateSectionCap();
}

function destroySectionPlane() {
	destroySectionCap();
	if (sectionTransformCtrl) {
		sectionTransformCtrl.detach();
		scene.remove(sectionTransformCtrl);
		sectionTransformCtrl.dispose();
		sectionTransformCtrl = null;
	}
	if (sectionPlaneMesh) {
		sectionPlaneMesh.geometry.dispose();
		sectionPlaneMesh.material.dispose();
		scene.remove(sectionPlaneMesh);
		sectionPlaneMesh = null;
	}
	sectionPlane = null;
	renderer.clippingPlanes = [];
	sectionPlaneMode = 'translate';
	const modeBtn = document.getElementById('section_plane_mode_btn');
	if (modeBtn) {
		modeBtn.style.display = 'none';
		modeBtn.title = 'Section: Move';
		const icon = modeBtn.querySelector('i');
		if (icon) icon.className = 'fa fa-arrows';
	}
	render();
}

function createSectionCap() {
	const baseMat = new THREE.MeshBasicMaterial({
		depthWrite: false,
		depthTest: false,
		colorWrite: false,
		stencilWrite: true,
		stencilFunc: THREE.AlwaysStencilFunc,
	});

	OdooCad.items.forEach(item => {
		item.traverse(child => {
			if (!(child instanceof THREE.Mesh)) return;
			child.updateMatrixWorld(true);

			// Back faces — increment stencil where geometry exits the clip plane
			const backMat = baseMat.clone();
			backMat.side = THREE.BackSide;
			backMat.clippingPlanes = [sectionPlane];
			backMat.stencilFail = THREE.IncrementWrapStencilOp;
			backMat.stencilZFail = THREE.IncrementWrapStencilOp;
			backMat.stencilZPass = THREE.IncrementWrapStencilOp;
			const backMesh = new THREE.Mesh(child.geometry, backMat);
			backMesh.matrixAutoUpdate = false;
			backMesh.matrix.copy(child.matrixWorld);
			backMesh.renderOrder = 1;
			scene.add(backMesh);
			sectionStencilMeshes.push(backMesh);

			// Front faces — decrement stencil where geometry enters the clip plane
			const frontMat = baseMat.clone();
			frontMat.side = THREE.FrontSide;
			frontMat.clippingPlanes = [sectionPlane];
			frontMat.stencilFail = THREE.DecrementWrapStencilOp;
			frontMat.stencilZFail = THREE.DecrementWrapStencilOp;
			frontMat.stencilZPass = THREE.DecrementWrapStencilOp;
			const frontMesh = new THREE.Mesh(child.geometry, frontMat);
			frontMesh.matrixAutoUpdate = false;
			frontMesh.matrix.copy(child.matrixWorld);
			frontMesh.renderOrder = 1;
			scene.add(frontMesh);
			sectionStencilMeshes.push(frontMesh);
		});
	});

	// Cap plane — rendered only where stencil ≠ 0 (the open cut surface)
	const w = sectionPlaneMesh.geometry.parameters.width;
	const h = sectionPlaneMesh.geometry.parameters.height;
	const capMat = new THREE.MeshBasicMaterial({
		color: 0xcccccc,
		stencilWrite: true,
		stencilRef: 0,
		stencilFunc: THREE.NotEqualStencilFunc,
		stencilFail: THREE.ReplaceStencilOp,
		stencilZFail: THREE.ReplaceStencilOp,
		stencilZPass: THREE.ReplaceStencilOp,
		depthWrite: false,
		depthTest: false,
	});
	sectionCapPlane = new THREE.Mesh(new THREE.PlaneGeometry(w, h), capMat);
	sectionCapPlane.renderOrder = 2;
	sectionCapPlane.position.copy(sectionPlaneMesh.position);
	sectionCapPlane.quaternion.copy(sectionPlaneMesh.quaternion);
	scene.add(sectionCapPlane);
}

function updateSectionCap() {
	if (!sectionCapPlane || !sectionPlaneMesh) return;
	sectionPlaneMesh.updateMatrixWorld();
	sectionCapPlane.position.copy(sectionPlaneMesh.position);
	sectionCapPlane.quaternion.copy(sectionPlaneMesh.quaternion);
}

function destroySectionCap() {
	for (const m of sectionStencilMeshes) {
		scene.remove(m);
		m.material.dispose();
	}
	sectionStencilMeshes.length = 0;
	if (sectionCapPlane) {
		scene.remove(sectionCapPlane);
		sectionCapPlane.geometry.dispose();
		sectionCapPlane.material.dispose();
		sectionCapPlane = null;
	}
}

document.getElementById("toggle_light_settings").onclick = function () {
	const group = document.getElementById("light_settings_group");

	if (group.style.display === "none") {
		group.style.display = "block";
		this.innerHTML = "<b>▼ Light Settings</b>";
	} else {
		group.style.display = "none";
		this.innerHTML = "<b>▶ Light Settings</b>";
	}
};


function fitCameraToSelection(selection, fitOffset = 1.2) {
	const box = new THREE.Box3();
	for (const object of Object.values(selection)) {
		if (object.visible) {
			box.expandByObject(object);
		}
	}
	const size = box.getSize(new THREE.Vector3());
	const center = box.getCenter(new THREE.Vector3());
	const maxSize = Math.max(size.x, size.y, size.z);
	const fitHeightDistance = maxSize / (2 * Math.atan(Math.PI * camera.fov / 360));
	const fitWidthDistance = fitHeightDistance / camera.aspect;
	const distance = fitOffset * Math.max(fitHeightDistance, fitWidthDistance);
	const direction = controls.target.clone()
		.sub(camera.position)
		.normalize()
		.multiplyScalar(distance);
	controls.minDistance = 0.01;
	controls.maxDistance = distance * 10;
	controls.target.copy(center);
	camera.near = distance / 100;
	camera.far = distance * 100;
	scene.fog.near = camera.far
	scene.fog.far = camera.far * 10
	camera.updateProjectionMatrix();
	camera.position.copy(controls.target).sub(direction);
	resetLight(box, maxSize);
	// sprite scale is now maintained per-frame in render()
	controls.update();
	render();
};

function addAmbient() {
	addCamera();
	addLight();
	addOrbit();
	/* add gradient background */
	scene.background = new THREE.Color(0xe0e0e0);
	scene.fog = new THREE.Fog(0xe0e0e0, 200, 1000);;
	// ground
	tecnicalBckground();
}

function togleBackgound() {
	if (togleBackgoundV) {
		togleBackgoundV = false;
		tecnicalBckground();
	}
	else {
		togleBackgoundV = true;
		imageBckground('/plm_web_3d/static/src/img/bakgroung_360/room.jpg');
	}
}

function tecnicalBckground() {
	objectAxesHelper.visible = true;
	planeMeshFloar = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000),
		new THREE.MeshPhongMaterial({ color: 0x999999, depthWrite: false, transparent: true, opacity: 0.15 }));
	planeGrid = new THREE.GridHelper(200, 40, 0x000000, 0x000000);
	planeMeshFloar.rotation.x = - Math.PI / 2;
	scene.add(planeMeshFloar);
	planeGrid.material.opacity = 0.2;
	planeGrid.material.transparent = true;
	planeGrid.receiveShadow = true;
	scene.add(planeGrid);
	planeGrid.visible = true;
	planeMeshFloar.visible = true;
	scene.background = new THREE.Color(0xe0e0e0);
	render();
}

var change_background = function () {
	var value = document.getElementById("webgl_background").value;
	switch (value) {
		case 'tecnical':
			tecnicalBckground();
			break;
		case 'room1':
			imageBckground('/plm_web_3d/static/src/img/bakgroung_360/room.jpg');
			break;
		case 'room2':
			imageBckground('/plm_web_3d/static/src/img/bakgroung_360/white_room.png');
			break;
		case 'workshop1':
			imageBckground('/plm_web_3d/static/src/img/bakgroung_360/workshop1.png');
			break;
		case 'workshop2':
			imageBckground('/plm_web_3d/static/src/img/bakgroung_360/workshop2.png');
			break;
		case 'workshop3':
			imageBckground('/plm_web_3d/static/src/img/bakgroung_360/workshop3.png');
			break;
		case 'outdoor':
			imageBckground('/plm_web_3d/static/src/img/bakgroung_360/outdoor.png');
			break;
		case 'clean':
			cleanBackground();
			break;
		default:
			tecnicalBckground();

	}
}

function cleanBackground() {
	objectAxesHelper.visible = false;
	planeGrid.visible = false;
	planeMeshFloar.visible = false;
	scene.background = new THREE.Color(0xf5f5f5);
	render();
}

function imageBckground(path_to_load) {
	objectAxesHelper.visible = false;
	const loader = new THREE.TextureLoader();
	planeGrid.visible = false;
	planeMeshFloar.visible = false;
	const texture = loader.load(
		path_to_load,
		() => {
			texture.encoding = THREE.sRGBEncoding;
			texture.mapping = THREE.EquirectangularReflectionMapping;
			const rt = new THREE.WebGLCubeRenderTarget(texture.image.height);
			rt.fromEquirectangularTexture(renderer, texture);

			scene.background = texture;

			const cubeCamera = new THREE.CubeCamera(1, 100000, rt);
			scene.add(cubeCamera);

			render();
			controls.update();
		});
}

function mesuraments() {
	const measurementDiv = document.createElement('div');
	const labelDiv = document.createElement('div');
	const close_button = document.createElement('button');
	close_button.type = "button";
	close_button.innerHTML = 'x';
	close_button.id = lineId;
	close_button.className = 'measurementButton';
	measurementDiv.className = 'measurement';
	labelDiv.className = 'measurementLabel';
	labelDiv.innerText = "0.0 mm";
	measurementDiv.appendChild(labelDiv);
	measurementDiv.appendChild(close_button);
	// remove the lable from scene
	close_button.addEventListener('pointerdown', function () {
		const id = close_button.id;
		scene.remove(measurementLabels[id]);
		scene.remove(endPoint[id]);
		scene.remove(startPoint[id]);
		scene.remove(lines[id]);
		_removeArrow(startArrow[id]);
		_removeArrow(endArrow[id]);
		delete startArrow[id];
		delete endArrow[id];
	});
	return measurementDiv;
}

function createMarker() {
	const snapType = (sphereHelper.userData && sphereHelper.userData.snapType) || 'vertex';
	const color = snapType === 'vertex' ? '#ffff00' : '#00ccff';
	const material = new THREE.SpriteMaterial({
		map: createSpriteTexture(color),
		depthTest: false,
		transparent: true,
	});
	const marker = new THREE.Sprite(material);
	marker.position.copy(sphereHelper.position);
	marker.scale.copy(sphereHelper.scale);
	marker.userData.snapType = snapType;
	scene.add(marker);
	return marker;
}

function show_all_scene_item() {
	var i;
	var tree_item_visibility = document.getElementsByClassName("tree_item_visibility");
	for (i = 0; i < tree_item_visibility.length; i++) {
		var icon = tree_item_visibility[i]
		icon.classList.remove('fa-eye-slash');
		icon.classList.add('fa-eye');
	}
	OdooCad.show_all();
}

function hide_all_scene_item() {
	var i;
	var tree_item_visibility = document.getElementsByClassName("tree_item_visibility");
	for (i = 0; i < tree_item_visibility.length; i++) {
		var icon = tree_item_visibility[i]
		icon.classList.remove('fa-eye');
		icon.classList.add('fa-eye-slash');
	}
	OdooCad.hide_all();
}

function init() {
	/*
	 * init function with basic definition
	 */
	canvas = document.getElementById('odoo_canvas');
	const main_3d_web = document.getElementById('main_3d_web');
	aspect = canvas.clientWidth / canvas.clientHeight;
	renderer = new THREE.WebGLRenderer({
		canvas,
		preserveDrawingBuffer: true
	});
	renderer.gammaInput = true;
	renderer.gammaOutput = true;
	renderer.localClippingEnabled = true;
	renderer.shadowMap.enabled = true;
	renderer.shadowMap.type = THREE.PCFSoftShadowMap; // default
	// THREE.PCFShadowMap
	/*
	 * Label Renderer
	 */
	var bounding_ret = canvas.getBoundingClientRect();
	labelRenderer = new CSS2DRenderer();
	labelRenderer.setSize(canvas.clientWidth, canvas.clientHeight);
	labelRenderer.domElement.style.position = 'absolute';
	labelRenderer.domElement.style.top = bounding_ret.y;
	labelRenderer.domElement.style.pointerEvents = 'none';
	main_3d_web.appendChild(labelRenderer.domElement);

	//
	// configure the raycaster
	//
	mouse = new THREE.Vector2();
	raycaster = new THREE.Raycaster();
	raycaster.params.Line.threshold = 3;
	raycaster.params.Points.threshold = 3;
	//
	// define scene and ambient
	//
	scene = new THREE.Scene();
	objectAxesHelper = new THREE.AxesHelper(500)
	scene.add(objectAxesHelper);
	addAmbient();
	createSphereHelper();
	//
	// load cube from html
	//
	cube = document.querySelector('.cube')
	//
	// Load document
	//
	var document_id = document.querySelector('#active_model').getAttribute('active_model');
	var document_name = document.querySelector('#active_model').getAttribute('document_name');
	/*
	 * inizialize OdooCAD
	 */
	OdooCad = new ODOOCAD.OdooCAD(scene);
	OdooCad.load_document(document_id, document_name);
	if (document_name && document_name.split('.').pop().toLowerCase() === 'dxf') {
		controls.enableRotate = false;
		if (cube) cube.style.display = 'none';
		if (planeMeshFloar) planeMeshFloar.visible = false;
		if (planeGrid) planeGrid.visible = false;
		if (objectAxesHelper) objectAxesHelper.visible = false;
		[
			document.getElementById('webgl_background')?.closest('.plm_button'),
			document.getElementById('toggle_light_settings'),
			document.getElementById('light_settings_group'),
			document.getElementById('object_transparency')?.closest('.plm_button'),
			document.getElementById('color_object_grp')?.closest('.plm_button'),
			document.getElementById('plm_button1'),
		].forEach(el => { if (el) el.style.display = 'none'; });
	}
	/*
	 * Inizialize tree view search
	 */
	// Commented the above as there is no id in the document with
	// input_search_document_tree present.
	//  var input_document_tree = document.getElementById('input_search_document_tree');
	var input_document_list = document.getElementById('input_search_document_list');
	input_document_list.addEventListener("keyup", OdooCad.search_document_tree);
	/*
	 * function to hide show all components
	 */
	var bnt_hide_all_parts = document.getElementById('hide_all_parts');
	bnt_hide_all_parts.addEventListener("click", hide_all_scene_item);


	var bnt_show_all_parts = document.getElementById('show_all_parts');
	bnt_show_all_parts.addEventListener("click", show_all_scene_item);

}

function getCameraCSSMatrix(matrix) {

	var elements = matrix.elements;

	return 'matrix3d(' +
		epsilon(elements[0]) + ',' +
		epsilon(-elements[1]) + ',' +
		epsilon(elements[2]) + ',' +
		epsilon(elements[3]) + ',' +
		epsilon(elements[4]) + ',' +
		epsilon(-elements[5]) + ',' +
		epsilon(elements[6]) + ',' +
		epsilon(elements[7]) + ',' +
		epsilon(elements[8]) + ',' +
		epsilon(-elements[9]) + ',' +
		epsilon(elements[10]) + ',' +
		epsilon(elements[11]) + ',' +
		epsilon(elements[12]) + ',' +
		epsilon(-elements[13]) + ',' +
		epsilon(elements[14]) + ',' +
		epsilon(elements[15]) +
		')';

}

function epsilon(value) {

	return Math.abs(value) < 1e-10 ? 0 : value;

}

function initcommand() {
	var selector = document.getElementById("webgl_background");
	selector.onchange = function (event) {
		change_background();
	}

	let click_show = document.getElementById("click_show");
	let activatorClick = document.getElementById("activatorClick");
	activatorClick.addEventListener("click", onActivatorClick);

	const markupLogsPerm = document.getElementById("markup_logs_perm");
	if (markupLogsPerm) markupLogsPerm.addEventListener("click", onMarkupLogsClick);

	click_show.addEventListener("click", on_data_card_button_click);

	// document.addEventListener('mousemove', onDocumentMousemove, false);
	// Fire onClick only for genuine clicks, not orbit drags.
	// Track pointer-down position and only call onClick on pointer-up when
	// the pointer has moved less than 6 px (i.e. it was not a drag/rotate).
	let _clickOriginX = 0, _clickOriginY = 0;
	const _zoomRectEl = document.getElementById("zoom_window_rect");
	document.addEventListener('pointerdown', (e) => {
		_clickOriginX = e.clientX;
		_clickOriginY = e.clientY;
		// Close part color picker if click is outside it
		const colorPopup = document.getElementById('part_color_popup');
		if (colorPopup && colorPopup.style.display !== 'none' && !colorPopup.contains(e.target)) {
			_hidePartColorPicker();
		}
		// Close transparency picker if click is outside it
		const transPopup = document.getElementById('part_transparency_popup');
		if (transPopup && transPopup.style.display !== 'none' && !transPopup.contains(e.target)) {
			_hidePartTransparencyPicker();
		}
		if (zoomWindowActive) {
			_zoomDragging = true;
			_zoomStartX = e.clientX;
			_zoomStartY = e.clientY;
			controls.enabled = false;
			if (_zoomRectEl) {
				_zoomRectEl.style.left = e.clientX + 'px';
				_zoomRectEl.style.top = e.clientY + 'px';
				_zoomRectEl.style.width = '0px';
				_zoomRectEl.style.height = '0px';
				_zoomRectEl.style.display = 'block';
			}
		}
	}, false);
	document.addEventListener('pointerup', (e) => {
		if (zoomWindowActive && _zoomDragging) {
			_zoomDragging = false;
			controls.enabled = true;
			if (_zoomRectEl) _zoomRectEl.style.display = 'none';
			const canvasRect = renderer.domElement.getBoundingClientRect();
			const x1 = Math.min(_zoomStartX, e.clientX) - canvasRect.left;
			const y1 = Math.min(_zoomStartY, e.clientY) - canvasRect.top;
			const selW = Math.abs(e.clientX - _zoomStartX);
			const selH = Math.abs(e.clientY - _zoomStartY);
			if (selW > 10 && selH > 10) zoomToWindow(x1, y1, selW, selH);
			_deactivateZoomWindow();
			return;
		}
		const dx = e.clientX - _clickOriginX;
		const dy = e.clientY - _clickOriginY;
		if (dx * dx + dy * dy < 36) onClick(e);
	}, false);
	document.addEventListener('pointermove', window.onPointerMove);
	// if (canvas) {
	// 	canvas.addEventListener('pointermove', window.onPointerMove);
	// }
	document.addEventListener('keydown', onKeyDone);
	document.addEventListener('keyup', onKeyup);


	// Permanent menu delegates → real buttons
	document.getElementById("fit_view_perm").onclick = function () {
		fitCameraToSelectionEvent();
	};
	document.getElementById("save_view_perm").onclick = function () {
		saveAsImage();
	};
	document.getElementById("markup_button_perm").onclick = function () {
		// markup lives in markup_system.js — call directly
		openMarkupEditor();
	};
	document.getElementById("show_all_perm").onclick = function () {
		show_all_scene_item();
	};
	document.getElementById("measure_btn_perm").onclick = function () {
		if (ctrlDown) _deactivateMeasure();
		else _activateMeasure();
	};

	// PLM object popup — event delegation on the data panel
	document.getElementById("main_div_hidden").addEventListener("click", function (e) {
		const el = e.target.closest(".plm_link");
		if (!el) return;
		const docId = el.dataset.docId;
		const prodId = el.dataset.prodId;
		if (docId) openOdooPopup("ir.attachment", docId);
		else if (prodId) openOdooPopup("product.product", prodId);
	});

	document.getElementById("zoom_window_btn").onclick = function () {
		if (zoomWindowActive) _deactivateZoomWindow();
		else _activateZoomWindow();
	};

	// Part color picker — apply color on change, sync tree input
	const partColorInput = document.getElementById('part_color_input');
	if (partColorInput) {
		partColorInput.addEventListener('input', function () {
			const guid = this._guid;
			if (!guid) return;
			const selectedColor = this.value;
			const groupObj = OdooCad.tree_ref_elements[guid];
			if (groupObj) {
				groupObj.traverse(child => {
					if (child instanceof THREE.Mesh && child.material) {
						child.material.color.setStyle(selectedColor);
						child.material.userData.originalColor = child.material.color.clone();
						child.material.userData.oldColor = child.material.color.clone();
					}
				});
				// Keep tree color swatch in sync
				const treeInput = document.querySelector(`.tree_item_color[webgl_ref_name="${guid}"]`);
				if (treeInput) treeInput.value = selectedColor;
				render();
			}
		});
		// Add to recents and update in-memory color map when user commits
		partColorInput.addEventListener('change', function () {
			_addRecentColor(this.value);
			_renderRecentColors();
			if (this._guid) {
				const groupObj = OdooCad.tree_ref_elements[this._guid];
				const partName = groupObj && groupObj.name;
				if (partName) {
					_partColors[partName] = this.value;
					_markAppearanceDirty();
				}
			}
		});
	}

	// Transparency slider — live apply, update in-memory opacity map
	const transparencySlider = document.getElementById('part_transparency_slider');
	if (transparencySlider) {
		transparencySlider.addEventListener('input', function () {
			const guid = this._guid;
			if (!guid) return;
			const opacity = parseInt(this.value, 10) / 100;
			const label = document.getElementById('part_transparency_label');
			if (label) label.textContent = this.value + '%';
			const groupObj = OdooCad.tree_ref_elements[guid];
			if (groupObj) {
				groupObj.traverse(child => {
					if (child instanceof THREE.Mesh && child.material) {
						const wasTransparent = child.material.transparent;
						child.material.transparent = opacity < 1.0;
						child.material.opacity = opacity;
						child.material.userData.originalOpacity = opacity;
						if (child.material.transparent !== wasTransparent) {
							child.material.needsUpdate = true;
						}
					}
				});
				const partName = groupObj.name;
				if (partName) {
					_partOpacity[partName] = opacity;
					_markAppearanceDirty();
				}
				render();
			}
		});
	}

	document.getElementById('transparency_btn_perm')?.addEventListener('click', () => {
		const guid = window.last_highlighted_li;
		if (guid && OdooCad?.tree_ref_elements?.[guid]) _showPartTransparencyPicker(guid);
	});

	document.getElementById("section_plane_btn").onclick = function () {
		sectionPlaneActive = !sectionPlaneActive;
		this.classList.toggle("active", sectionPlaneActive);
		if (sectionPlaneActive) createSectionPlane();
		else destroySectionPlane();
	};

	document.getElementById("section_plane_mode_btn").onclick = function () {
		if (!sectionTransformCtrl) return;
		sectionPlaneMode = sectionPlaneMode === 'translate' ? 'rotate' : 'translate';
		sectionTransformCtrl.setMode(sectionPlaneMode);
		const icon = this.querySelector('i');
		if (icon) icon.className = sectionPlaneMode === 'translate' ? 'fa fa-arrows' : 'fa fa-repeat';
		this.title = sectionPlaneMode === 'translate' ? 'Section: Move' : 'Section: Rotate';
	};

	const helpBtn = document.getElementById("help_btn");
	const shortcutModal = document.getElementById("shortcut_modal");
	const shortcutClose = document.getElementById("shortcut_modal_close");
	helpBtn.onclick = function () {
		shortcutModal.classList.add("open");
	};
	shortcutClose.onclick = function () {
		shortcutModal.classList.remove("open");
	};
	shortcutModal.addEventListener("click", function (e) {
		if (e.target === shortcutModal) shortcutModal.classList.remove("open");
	});

	_partColorsDocId = parseInt(
		document.querySelector('#active_model')?.getAttribute('active_model') || '0', 10
	) || null;

	const html_canvas = document.getElementById('odoo_canvas');
	html_canvas.addEventListener("OdooCAD_fit_items", fitCameraToSelectionEvent, false);
	html_canvas.addEventListener("OdooCAD_fit_items", function _loadSavedColors() {
		html_canvas.removeEventListener("OdooCAD_fit_items", _loadSavedColors);
		if (!_partColorsDocId) return;
		fetch(`/plm/part_colors/load?document_id=${_partColorsDocId}`)
			.then(r => r.json())
			.then(stored => {
				if (stored && Object.keys(stored).length > 0) {
					_applyPartAppearance(stored);
					render();
				}
			})
			.catch(e => console.warn('part_colors load failed', e));
	}, false);
	html_canvas.addEventListener("OdooCAD_render", () => { render(); }, false);

	document.getElementById('save_part_colors_btn').addEventListener('click', _savePartColors);
	document.getElementById('save_preview_btn').addEventListener('click', savePreviewToOdoo);
	// light
	var object_light_distance = document.getElementById("object_distance")
	object_light_distance.oninput = chenge_light_distance;
	var object_light1 = document.getElementById("object_light1");
	object_light1.oninput = chenge_light1;
	var object_light2 = document.getElementById("object_light2");
	object_light2.oninput = chenge_light2;
	var object_light3 = document.getElementById("object_light3");
	object_light3.oninput = chenge_light3;
	var object_light_camera = document.getElementById("object_light_camera");
	object_light_camera.oninput = chenge_light_camera;
	var object_light_ambient = document.getElementById("object_light_ambient");
	object_light_ambient.oninput = chenge_light_ambient;

	var object_transparency = document.getElementById("object_transparency");
	object_transparency.oninput = change_object_transparency;

	var object_explosion = document.getElementById("object_explosion");
	object_explosion.oninput = change_object_explosion;
	/*
	 * Load datacard
	 */
	var document_id = document.querySelector('#active_model').getAttribute('active_model');
	var xmlhttp = new XMLHttpRequest();
	var url = "/plm/get_product_info?document_id=" + document_id;

	xmlhttp.onreadystatechange = function () {
		if (this.readyState == 4 && this.status == 200) {
			var responseText = this.responseText.trim();
			if (responseText.startsWith("<!DOCTYPE") || responseText.startsWith("<html")) {
				console.error("Received HTML instead of JSON. Session might be expired.");
				return;
			}
			try {
				var result = JSON.parse(responseText);
				var product_info = document.getElementById("product_info");
				if (product_info) product_info.innerHTML = result['component'];
				var document_info = document.getElementById("document_info");
				if (document_info) document_info.innerHTML = result['document'];
			} catch (e) {
				console.error("Error parsing product info JSON:", e);
			}
		}
	};
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}
function onActivatorClick(event) {
	const activatorDiv = document.getElementById("activatorDiv");
	const btn = document.getElementById("activatorClick");
	const isOpen = !activatorDiv.classList.contains('d-none');
	if (isOpen) {
		activatorDiv.style.visibility = 'hidden';
		activatorDiv.style.opacity = 0;
		activatorDiv.classList.add('d-none');
		btn?.classList.remove('active');
	} else {
		activatorDiv.style.visibility = 'visible';
		activatorDiv.style.opacity = 0.95;
		activatorDiv.classList.remove('d-none');
		btn?.classList.add('active');
	}
}

function onMarkupLogsClick(event) {
	const panel = document.getElementById("markup_logs_panel");
	const btn = document.getElementById("markup_logs_perm");
	if (!panel) return;
	const isOpen = !panel.classList.contains('d-none');
	if (isOpen) {
		panel.style.visibility = 'hidden';
		panel.style.opacity = 0;
		panel.classList.add('d-none');
		btn?.classList.remove('active');
	} else {
		panel.style.visibility = 'visible';
		panel.style.opacity = 0.95;
		panel.classList.remove('d-none');
		btn?.classList.add('active');
	}
}

function on_data_card_button_click(event) {
	// highlight the mouseover target
	let main_div = document.getElementById("main_div");
	if (clicked) {
		main_div.style.visibility = 'invisible';
		main_div.style.opacity = 0;
	}
	else {
		main_div.style.visibility = 'visible';
		main_div.style.opacity = 0.8;
	}
	clicked = !clicked;
}

function saveAsImage() {
	var imgData, imgNode;
	try {
		var document_name = document.querySelector('#active_model').getAttribute('document_name');
		var strMime = "image/jpeg";
		imgData = renderer.domElement.toDataURL(strMime);

		saveFile(imgData.replace(strMime, strDownloadMime), document_name + ".jpg");

	} catch (e) {
		console.log(e);
		return;
	}

}

function savePreviewToOdoo() {
	if (!_partColorsDocId) return;
	const btn = document.getElementById('save_preview_btn');

	// Center-square crop so the preview thumbnail is not stretched
	const src = renderer.domElement;
	const w = src.width, h = src.height;
	const side = Math.min(w, h);
	const offsetX = Math.floor((w - side) / 2);
	const offsetY = Math.floor((h - side) / 2);
	const squareCanvas = document.createElement('canvas');
	squareCanvas.width = side;
	squareCanvas.height = side;
	squareCanvas.getContext('2d').drawImage(src, offsetX, offsetY, side, side, 0, 0, side, side);
	const base64 = squareCanvas.toDataURL('image/jpeg', 0.85).split(',')[1];
	fetch('/plm/save_preview', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			jsonrpc: '2.0', method: 'call', id: 1,
			params: { document_id: _partColorsDocId, image_data: base64 },
		}),
	})
		.then(r => r.json())
		.then(data => {
			const ok = data.result && data.result.success;
			if (btn) {
				btn.classList.add(ok ? 'color-save-ok' : 'color-save-err');
				setTimeout(() => btn.classList.remove('color-save-ok', 'color-save-err'), 1500);
			}
		})
		.catch(() => {
			if (btn) {
				btn.classList.add('color-save-err');
				setTimeout(() => btn.classList.remove('color-save-err'), 1500);
			}
		});
}

var saveFile = function (strData, filename) {
	var link = document.createElement('a');
	if (typeof link.download === 'string') {
		document.body.appendChild(link); // Firefox requires the link to be
		// in the body
		link.download = filename;
		link.href = strData;
		link.click();
		document.body.removeChild(link); // remove the link when done
	} else {
		location.replace(uri);
	}
}

var apply_transparency = function (item, value) {
	var material = item.material;

	if (value) {
		if (value > 99.9) {
			material.transparent = false;
			material.alphaTest = false;
		} else {
			material.side = THREE.DoubleSide;
			material.transparent = true;
			material.opacity = value / 100;
			material.alphaTest = 0.1;
		}
	}
	else {
		material.transparent = true;
		material.opacity = 0;
	}
}
var change_object_transparency = function (event) {
	var items = OdooCad.items;
	var value = this.value;
	for (let i = 0; i < items.length; i = i + 1) {
		var loop_item = items[i];
		loop_item.traverse(function (child_mesh) {
			if (child_mesh.type == "Mesh") {
				apply_transparency(child_mesh, value);
			}
		});
	}
}
var chenge_light_distance = function (event) {
	var value = this.value;
	change_light_position(value / 1000);
}
var chenge_light1 = function (event) {
	var value = this.value;
	light1.intensity = value / 100;
}
var chenge_light2 = function (event) {
	var value = this.value;
	light2.intensity = value / 100;
}
var chenge_light3 = function (event) {
	var value = this.value;
	light3.intensity = value / 100;
}
var chenge_light_ambient = function (event) {
	var value = this.value;
	ambientLight.intensity = value / 100;
}
var chenge_light_camera = function (event) {
	var value = this.value;
	cameraLight.intensity = value / 100;
}

var change_object_explosion = function (event) {
	var value = parseFloat(this.value);

	// Store original positions only once before first explosion
	if (!_explosionInitialized) {
		storeOriginalPositions();
		_explosionInitialized = true;
	}

	// Slider back to 0 → restore all original positions
	if (value === 0) {
		for (const [guid, obj] of Object.entries(OdooCad.tree_ref_elements)) {
			var orig = _originalPositions.get(guid);
			if (orig) obj.position.copy(orig);
		}
		render();
		return;
	}

	// Compute bounding box of all entities to get the true global center
	const allBBox = new THREE.Box3();
	for (const obj of Object.values(OdooCad.tree_ref_elements)) {
		allBBox.expandByObject(obj);
	}
	const center = new THREE.Vector3();
	allBBox.getCenter(center);
	const size = allBBox.getSize(new THREE.Vector3());
	const maxSize = Math.max(size.x, size.y, size.z);

	// Explode each named tree item independently
	for (const [guid, obj] of Object.entries(OdooCad.tree_ref_elements)) {
		explode(obj, guid, center, value, maxSize);
	}

	render();
}


var fitCameraToSelectionEvent = function (e) {
	if (Object.values(OdooCad.tree_ref_elements).length > 0) {
		fitCameraToSelection(OdooCad.tree_ref_elements, 1.1);
		return
	}
	fitCameraToSelection(OdooCad.items, 1.1);
}

/**
 * Mouse coordinates go from 0 to container width {0:1} and 0 to container
 * height {0:1}. Multiply by 2 and subtract 1 to center the mouse coords {-1:1}.
 * Furthermore, negate the y axis coords, as in the DOM the origin is in the top
 * left corner, while in WebGL the origin is in the bottom left corner.
 */
/*
 * var onDocumentMousemove = function (e) { mouse.x = ( event.clientX /
 * canvas.clientWidth ) * 2 - 1; mouse.y = - ( event.clientY /
 * canvas.clientHeight ) * 2 + 1; }
 */
var onClick = function (e) {
	if (ctrlDown) {
		if (!lines[lineId]) {
			// start the line
			const points = [];
			points.push(sphereHelper.position);
			points.push(sphereHelper.position.clone());
			const geometry = new THREE.BufferGeometry().setFromPoints(points);
			lines[lineId] = new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({
				color: 0x714B67,
				transparent: true,
				linewidth: 2,
				opacity: 0.9,
				depthTest: false,
				depthWrite: false,
			}));
			lines[lineId].frustumCulled = false;
			const measurementLabel = new CSS2DObject(mesuraments());
			measurementLabel.position.copy(sphereHelper.position);
			measurementLabels[lineId] = measurementLabel;
			startSnapTypes[lineId] = (sphereHelper.userData && sphereHelper.userData.snapType) || 'vertex';
			startPoint[lineId] = createMarker();
			scene.add(measurementLabels[lineId]);
			scene.add(lines[lineId]);
			drawingLine = true;
		}
		else {
			// finish the line
			const positions = lines[lineId].geometry.attributes.position.array;
			const startVec = new THREE.Vector3(positions[0], positions[1], positions[2]);
			const endVec = sphereHelper.position.clone();
			positions[3] = endVec.x;
			positions[4] = endVec.y;
			positions[5] = endVec.z;
			lines[lineId].geometry.attributes.position.needsUpdate = true;
			endSnapTypes[lineId] = (sphereHelper.userData && sphereHelper.userData.snapType) || 'vertex';
			endPoint[lineId] = createMarker();
			startArrow[lineId] = createArrowSprite(SNAP_ARROW_COLOR[startSnapTypes[lineId]] || '#ffff88');
			startArrow[lineId].position.copy(startVec);
			endArrow[lineId] = createArrowSprite(SNAP_ARROW_COLOR[endSnapTypes[lineId]] || '#88eeff');
			endArrow[lineId].position.copy(endVec);
			// update label with final distance at midpoint
			const dist = startVec.distanceTo(endVec);
			const mid = new THREE.Vector3().addVectors(startVec, endVec).multiplyScalar(0.5);
			if (measurementLabels[lineId]) {
				measurementLabels[lineId].position.copy(mid);
				const lbl = measurementLabels[lineId].element.querySelector('.measurementLabel');
				if (lbl) {
					const sType = startSnapTypes[lineId] === 'vertex' ? 'P' : 'F';
					const eType = endSnapTypes[lineId] === 'vertex' ? 'P' : 'F';
					lbl.innerText = `${sType}→${eType}: ${dist.toFixed(2)} mm`;
				}
			}
			drawingLine = false;
			lineId++;
		}
	} else {
		// 3D part color Feature
		if (window.last_highlighted_li) {
			const guid = window.last_highlighted_li;
			const part = OdooCad.tree_ref_elements[guid];
			if (part) {
				// Global color picker removed in favor of tree-based pickers
				/*
				const colorInput = document.getElementById("object_color");
				if (colorInput) {
					const selectedColor = colorInput.value;
					part.traverse(function (child) {
						if (child instanceof THREE.Mesh && child.material) {
							child.material.color.setStyle(selectedColor);
							// Update persistence for highlighting systems
							child.material.userData.originalColor = child.material.color.clone();
							child.material.userData.oldColor = child.material.color.clone();
						}
					});
					render();
				}
				*/
			}
		}
	}

}

/**
 * OdooCADApplication.js
 * Final Version: Deep Search & Forced Container Scroll
 */

// 1. GLOBAL STATE & SAFETY
if (typeof window.last_highlighted_li === 'undefined') {
	window.last_highlighted_li = null;
}
if (typeof window.last_highlighted_sidebar_el === 'undefined') {
	window.last_highlighted_sidebar_el = null;
}
window.ODOO_HILIGHT_COLOR = new THREE.Color("#eda3da");
window.tooltipCache = {};
window.tooltipTimer = null;
window.tooltipPendingGuid = null;


// Helper to expand all parent folders in the sidebar tree
function expandAncestors(element) {
	let parent = element.parentElement;
	while (parent && parent.id !== 'document_tree') {
		if (parent.tagName === 'UL' && parent.classList.contains('nested')) {
			parent.classList.add('active');
			// Find the toggler span (caret) on the previous sibling or parent LI
			const li = parent.closest('li');
			if (li) {
				const caret = li.querySelector('.caret');
				if (caret) caret.classList.add('caret-down');
			}
		}
		parent = parent.parentElement;
	}
}


window.highlight3D = function (guid, enable = true) {
	if (!OdooCad?.tree_ref_elements?.[guid]) return;
	const obj = OdooCad.tree_ref_elements[guid];
	obj.traverse((child) => {
		if (!(child instanceof THREE.Mesh) || !child.material) return;
		if (enable) {
			if (!child.material.userData.originalColor) {
				child.material.userData.originalColor = child.material.color.clone();
			}
			child.material.color.copy(window.ODOO_HILIGHT_COLOR);
			if (!child.getObjectByName('__highlight_edges__')) {
				const edges = new THREE.EdgesGeometry(child.geometry);
				const edgeMat = new THREE.LineBasicMaterial({ color: 0x714B67 });
				const wireframe = new THREE.LineSegments(edges, edgeMat);
				wireframe.name = '__highlight_edges__';
				wireframe.raycast = () => { };
				child.add(wireframe);
			}
		} else {
			if (child.material.userData.originalColor) {
				child.material.color.copy(child.material.userData.originalColor);
			}
			const wireframe = child.getObjectByName('__highlight_edges__');
			if (wireframe) {
				child.remove(wireframe);
				wireframe.geometry.dispose();
				wireframe.material.dispose();
			}
		}
	});
	if (typeof render === "function") render();
};


window.onPointerMove = function (event) {
	if (typeof canvas === 'undefined' || !canvas) return;
	if (typeof raycaster === 'undefined' || typeof camera === 'undefined') return;

	_lastPointerX = event.clientX;
	_lastPointerY = event.clientY;

	// While drawing the zoom rectangle, update its size and skip everything else
	if (zoomWindowActive && _zoomDragging) {
		const rectEl = document.getElementById("zoom_window_rect");
		if (rectEl) {
			const x = Math.min(_zoomStartX, event.clientX);
			const y = Math.min(_zoomStartY, event.clientY);
			rectEl.style.left = x + 'px';
			rectEl.style.top = y + 'px';
			rectEl.style.width = Math.abs(event.clientX - _zoomStartX) + 'px';
			rectEl.style.height = Math.abs(event.clientY - _zoomStartY) + 'px';
		}
		return;
	}

	const rect = canvas.getBoundingClientRect();
	const x = event.clientX - rect.left;
	const y = event.clientY - rect.top;

	pointer.x = (x / canvas.clientWidth) * 2 - 1;
	pointer.y = -(y / canvas.clientHeight) * 2 + 1;

	raycaster.setFromCamera(pointer, camera);
	const intersects = raycaster.intersectObjects(OdooCad.items, true);

	let hoveredGuid = null;
	if (intersects.length > 0) {
		let obj = intersects[0].object;
		let foundGuid = null;
		while (obj) {
			if (obj.userData && obj.userData.webgl_ref_name) {
				let nodeName = (obj.name || "").toLowerCase();
				if (!nodeName.startsWith("body")) {
					foundGuid = obj.userData.webgl_ref_name;
					break;
				} else if (!foundGuid) {
					foundGuid = obj.userData.webgl_ref_name;
				}
			}
			obj = obj.parent;
		}
		hoveredGuid = foundGuid;
	}

	// --- TOOLTIP LOGIC ---
	const tooltip = document.getElementById('part_tooltip');
	if (!tooltip) {
		console.warn("Tooltip element #part_tooltip not found in DOM");
	} else if (hoveredGuid) {
		// Always track cursor so the tooltip appears at the right position when it shows
		tooltip.style.left = (event.clientX + 15) + 'px';
		tooltip.style.top = (event.clientY + 15) + 'px';

		if (hoveredGuid !== window.tooltipPendingGuid) {
			// Moved to a new object — hide any visible tooltip and restart the delay
			tooltip.style.display = 'none';
			tooltip.innerText = '';
			clearTimeout(window.tooltipTimer);
			window.tooltipPendingGuid = hoveredGuid;

			window.tooltipTimer = setTimeout(function () {
				const guid = window.tooltipPendingGuid;
				if (!guid) return;
				tooltip.style.display = 'block';

				const obj3d = OdooCad.tree_ref_elements[guid];
				if (obj3d) {
					const srcName = (obj3d.userData && obj3d.userData.engineering_code) || obj3d.name || obj3d.type || "Component";

					if (window.tooltipCache[srcName]) {
						tooltip.innerText = window.tooltipCache[srcName];
					} else {
						tooltip.innerText = srcName;
						const parentId = document.getElementById('main_3d_web')?.getAttribute('data-res-id') || document.getElementById('active_model')?.getAttribute('active_model') || "";
						const url = `/plm/get_3d_web_document_info?src_name=${encodeURIComponent(srcName)}&parent_id=${parentId}`;
						fetch(url)
							.then(response => response.text())
							.then(data => {
								const trimmedData = data.trim();
								if (trimmedData.startsWith("<!DOCTYPE") || trimmedData.startsWith("<html")) {
									// Session lost or error page — don't show HTML in tooltip
									window.tooltipCache[srcName] = srcName;
									return;
								}
								const finalMsg = trimmedData || srcName;
								window.tooltipCache[srcName] = finalMsg;
								if (window.tooltipPendingGuid === guid) {
									tooltip.innerText = finalMsg;
								}
							})
							.catch(err => {
								console.error("Tooltip error:", err);
								window.tooltipCache[srcName] = srcName;
							});
					}
				} else {
					tooltip.innerText = "Unknown Part";
				}
			}, 1000);
		}
	} else {
		clearTimeout(window.tooltipTimer);
		window.tooltipPendingGuid = null;
		tooltip.style.display = 'none';
		tooltip.innerText = '';
	}


	// --- HIGHLIGHT SYNC LOGIC ---
	if (hoveredGuid !== window.last_highlighted_li) {
		if (window.last_highlighted_li) {
			window.highlight3D(window.last_highlighted_li, false);
		}

		if (window.last_highlighted_sidebar_el) {
			const el = window.last_highlighted_sidebar_el;
			el.classList.remove('document_tree_line_highlighted');
			el.style.backgroundColor = "";
			el.style.color = "";
			el.style.border = "";
			el.style.boxShadow = "";
			const children = el.querySelectorAll('span, i');
			children.forEach(c => {
				c.style.backgroundColor = "";
				c.style.color = "";
			});
			window.last_highlighted_sidebar_el = null;
		}

		if (hoveredGuid) {
			window.highlight3D(hoveredGuid, true);
			let targetLi = document.querySelector(`li[webgl_ref_name="${hoveredGuid}"]`);
			if (!targetLi) {
				const span = document.querySelector(`span[webgl_ref_name="${hoveredGuid}"]`);
				if (span) targetLi = span.closest('li');
			}

			if (targetLi) {
				const highlightColor = "#eda3da";
				const textColor = "#000000";
				expandAncestors(targetLi);
				targetLi.classList.add('document_tree_line_highlighted');
				targetLi.style.setProperty('background-color', highlightColor, 'important');
				targetLi.style.setProperty('color', textColor, 'important');
				targetLi.style.setProperty('border', '2px solid #714B67', 'important');
				targetLi.style.setProperty('box-shadow', '0 0 14px rgba(113, 75, 103, 0.7)', 'important');
				targetLi.style.borderRadius = "4px";
				window.last_highlighted_sidebar_el = targetLi;

				const subElements = targetLi.querySelectorAll('span, i');
				subElements.forEach(sub => {
					sub.style.setProperty('background-color', highlightColor, 'important');
					sub.style.setProperty('color', textColor, 'important');
				});

				targetLi.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
			}
		}
		window.last_highlighted_li = hoveredGuid;
	}
	if (typeof render === "function") render();
};


// 4. ATTACH EVENT LISTENER SAFELY
// Remove existing listener first to prevent multiple triggers if script reloads
document.removeEventListener('pointermove', window.onPointerMove);
document.addEventListener('pointermove', window.onPointerMove);

function onKeyDone(event) {
	if (event.key === "Control") {
		if (ctrlDown) _deactivateMeasure();
		else _activateMeasure();
		return;
	}
	if (event.key === "Escape") {
		const colorPopup = document.getElementById('part_color_popup');
		if (colorPopup && colorPopup.style.display !== 'none') {
			_hidePartColorPicker();
			return;
		}
		const transPopup = document.getElementById('part_transparency_popup');
		if (transPopup && transPopup.style.display !== 'none') {
			_hidePartTransparencyPicker();
			return;
		}
		if (zoomWindowActive) _deactivateZoomWindow();
		else if (ctrlDown) _deactivateMeasure();
		return;
	}
	if (event.key === 'w' || event.key === 'W') {
		if (zoomWindowActive) _deactivateZoomWindow();
		else _activateZoomWindow();
		return;
	}
	const tag = (event.target || document.activeElement || {}).tagName || '';
	if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
	if (event.key === 'c' || event.key === 'C') {
		const guid = window.last_highlighted_li;
		if (guid && OdooCad?.tree_ref_elements?.[guid]) _showPartColorPicker(guid);
		return;
	}
	if (event.key === 't' || event.key === 'T') {
		const guid = window.last_highlighted_li;
		if (guid && OdooCad?.tree_ref_elements?.[guid]) _showPartTransparencyPicker(guid);
		return;
	}
	if (event.key === 'f' || event.key === 'F') {
		fitCameraToSelectionEvent();
	}
	if (event.key === 'a' || event.key === 'A') {
		show_all_scene_item();
		render();
	}
	if (event.key === 'h' || event.key === 'H') {
		const guid = window.last_highlighted_li;
		if (guid && OdooCad?.tree_ref_elements?.[guid]) {
			const obj = OdooCad.tree_ref_elements[guid];
			const show = !obj.visible;
			obj.visible = show;
			// sync sidebar eye icon
			let targetLi = document.querySelector(`li[webgl_ref_name="${guid}"]`);
			if (!targetLi) {
				const span = document.querySelector(`span[webgl_ref_name="${guid}"]`);
				if (span) targetLi = span.closest('li');
			}
			if (targetLi) {
				const icon = targetLi.querySelector('.tree_item_visibility');
				if (icon) {
					icon.classList.toggle('fa-eye', show);
					icon.classList.toggle('fa-eye-slash', !show);
				}
			}
			if (!show) {
				// remove highlight/edges when hiding; keep last_highlighted_li so a
				// second h-press (without moving the mouse) can toggle it back
				window.highlight3D(guid, false);
			}
			render();
		}
	}
}


function onKeyup(event) {
	// Control key release is intentionally ignored — measure mode is toggled
	// by pressing Ctrl (or the toolbar button) and closed with Esc.
}

function inIframe() {
	try {
		return window.self !== window.top;
	} catch (e) {
		return true;
	}
}

function addCamera() {
	camera = new THREE.PerspectiveCamera(fov,
		aspect,
		near,
		far);
	camera.position.z = 2;
	// light
	cameraLight = new THREE.PointLight(0xffffff, 0.5);
	camera.add(cameraLight);
	scene.add(camera);
}

function addOrbit() {
	controls = new OrbitControls(camera, renderer.domElement);
	controls.addEventListener('change', render);
	controls.minDistance = 2;
	controls.maxDistance = 10;
	controls.rotateSpeed = 0.5
	controls.target.set(0, 0, - 0.2);
	controls.update();
}

function resetLight(bbox, size) {
	bbox_center = new THREE.Vector3();
	bbox.getCenter(bbox_center);
	change_light_position(size)
}

function change_light_position(size) {
	var mult = size * 1000;
	//
	var x = bbox_center.x + mult;
	var y = bbox_center.y + mult;
	var z = bbox_center.z + mult;
	//
	light1.position.z = z;
	light1.position.y = - y;
	light1.position.x = - x;
	//
	light2.position.z = z;
	light2.position.x = - x;
	light2.position.y = y;
	//
	light3.position.z = z;
	light3.position.x = x;
	light3.position.y = - y;
}

function addLight() {
	const sphereSize = 20;
	const group = new THREE.Group();
	scene.add(group);

	light1 = new THREE.SpotLight(0xf7d962, 0.1);
	light1.castShadow = true; // default false
	light1.position.z = 70;
	light1.position.y = - 70;
	light1.position.x = - 70;
	light1.intensity = 0.5;
	scene.add(light1);

	light2 = new THREE.SpotLight(0xffdddd, 0.1);
	light2.castShadow = true; // default false
	light2.position.z = 70;
	light2.position.x = - 70;
	light2.position.y = 70;
	light2.intensity = 0.5;
	scene.add(light2);

	light3 = new THREE.SpotLight(0xf7d962, 0.1);
	light3.castShadow = true; // default false
	light3.position.z = 70;
	light3.position.x = 70;
	light3.position.y = - 70;
	light3.intensity = 0.1;
	scene.add(light3);

	ambientLight = new THREE.HemisphereLight('#b199ff',        // bright sky color
		'darkslategrey',  // dim ground color
		0.1,              // intensity
	);

	scene.add(ambientLight);
	if (DEBUG_SCENE) {
		let i = 0;
		const lights = [light1, light2, light3];
		while (i < lights.length) {
			var directionalLightHelper = new THREE.DirectionalLightHelper(lights[i]);
			scene.add(directionalLightHelper);
			i++;
		}

	}
}

function showSnapPoint() {
	if (!sphereHelper) return;
	raycaster.setFromCamera(pointer, camera);
	const intersections = raycaster.intersectObjects(OdooCad.items, true);
	const intersection = intersections.length > 0 ? intersections[0] : null;
	if (!intersection) {
		sphereHelper.visible = false;
		return;
	}

	// Find nearest vertex in correct world space (handles rotation + scale)
	const matWorld = intersection.object.matrixWorld;
	const verts = intersection.object.geometry.attributes.position.array;
	let nearestVertex = null;
	let minDist = Infinity;
	const tmp = new THREE.Vector3();
	for (let i = 0; i < verts.length; i += 3) {
		tmp.set(verts[i], verts[i + 1], verts[i + 2]).applyMatrix4(matWorld);
		const d = intersection.point.distanceTo(tmp);
		if (d < minDist) { minDist = d; nearestVertex = tmp.clone(); }
	}

	// Pixel-space snap threshold — scale-independent
	const distCam = camera.position.distanceTo(intersection.point);
	const vFovRad = camera.fov * Math.PI / 180;
	const worldPerPx = (2 * distCam * Math.tan(vFovRad / 2)) / renderer.domElement.clientHeight;
	const snapThreshold = 20 * worldPerPx;

	const isVertex = nearestVertex !== null && minDist < snapThreshold;
	const snapPoint = isVertex ? nearestVertex : intersection.point.clone();
	const snapType = isVertex ? 'vertex' : 'face';
	const snapColor = isVertex ? '#ffff00' : '#00ccff';

	// Update sphere texture only when snap type changes (avoid per-frame alloc)
	if (sphereHelper.userData.snapType !== snapType) {
		sphereHelper.userData.snapType = snapType;
		sphereHelper.material.map = createSpriteTexture(snapColor);
		sphereHelper.material.needsUpdate = true;
	}
	sphereHelper.position.copy(snapPoint);
	sphereHelper.visible = true;

	// Live preview while drawing a measurement line
	if (drawingLine && lines[lineId]) {
		const pos = lines[lineId].geometry.attributes.position.array;
		pos[3] = snapPoint.x;
		pos[4] = snapPoint.y;
		pos[5] = snapPoint.z;
		lines[lineId].geometry.attributes.position.needsUpdate = true;
		const startVec = new THREE.Vector3(pos[0], pos[1], pos[2]);
		const liveDist = startVec.distanceTo(snapPoint);
		const liveMid = new THREE.Vector3().addVectors(startVec, snapPoint).multiplyScalar(0.5);
		if (measurementLabels[lineId]) {
			measurementLabels[lineId].position.copy(liveMid);
			const lbl = measurementLabels[lineId].element.querySelector('.measurementLabel');
			if (lbl) {
				const sType = startSnapTypes[lineId] === 'vertex' ? 'P' : 'F';
				lbl.innerText = `${sType}→${snapType === 'vertex' ? 'P' : 'F'}: ${liveDist.toFixed(2)} mm`;
			}
		}
	}
}

function updateOrientationCube(camera) {
	if (cube) {
		const mat = new THREE.Matrix4();
		mat.extractRotation(camera.matrixWorldInverse);
		cube.style.transform = `translateZ(-100px) ${getCameraCSSMatrix(mat)}`;
	}
}

function render() {
	if (debug_3d) {
		console.log("position");
		console.log(camera.position);
		console.log("rotation");
		console.log(camera.rotation);
	}
	resizeCanvasToDisplaySize();
	showSnapPoint();
	// Keep all measurement sprites at a constant screen-space size.
	const MARKER_PX = 14;
	if (sphereHelper && sphereHelper.visible) {
		_scaleSpriteToPixels(sphereHelper, MARKER_PX);
	}
	Object.values(startPoint).forEach(s => { if (s) _scaleSpriteToPixels(s, MARKER_PX); });
	Object.values(endPoint).forEach(s => { if (s) _scaleSpriteToPixels(s, MARKER_PX); });
	// Update arrow sprites: align rotation to projected line direction each frame
	Object.keys(startArrow).forEach(id => {
		const sa = startArrow[id];
		const ea = endArrow[id];
		if (!sa || !ea) return;
		const sp = sa.position.clone().project(camera);
		const ep = ea.position.clone().project(camera);
		const angle = Math.atan2(ep.y - sp.y, ep.x - sp.x);
		sa.material.rotation = angle + Math.PI; // points away from end
		ea.material.rotation = angle;            // points toward end
		_scaleSpriteToPixels(sa, 22);
		_scaleSpriteToPixels(ea, 22);
	});
	updateOrientationCube(camera);
	labelRenderer.render(scene, camera);
	renderer.render(scene, camera);
	Object.values(measurementLabels).forEach(label => {
		if (label) {
			label.lookAt(camera.position);
		}
	});
}

function tweenCamera(position) {
	controls.target = new THREE.Vector3(0, 0, 0);
	console.log(position);
	const { offsetFactor, axisAngle } = defined_orientation[position];
	console.log(offsetFactor);
	const offsetUnit = camera.position.length();
	const offset = new THREE.Vector3(
		offsetUnit * offsetFactor.x,
		offsetUnit * offsetFactor.y,
		offsetUnit * offsetFactor.z
	);

	const center = new THREE.Vector3();
	const finishPosition = center.add(offset);
	console.log("-> new camera position: ");
	console.log(finishPosition);
	camera.position.set(offset.x,
		offset.y,
		offset.z);
	//controls.update();
	fitCameraToSelection(OdooCad.tree_ref_elements,
		1.1);
	//render();
}

function resizeCanvasToDisplaySize() {
	canvas = renderer.domElement;
	// look up the size the canvas is being displayed
	const clientWidth = canvas.clientWidth;
	const clientHeight = canvas.clientHeight;
	// adjust displayBuffer size to match
	if (canvas.width !== clientWidth || canvas.height !== clientHeight) {
		// you must pass false here or three.js sadly fights the browser
		camera.aspect = clientWidth / clientHeight;
		camera.updateProjectionMatrix();
		renderer.setSize(clientWidth, clientHeight);
		labelRenderer.setSize(clientWidth, clientHeight);
	}
	if (cube) {
		cube.style.left = clientWidth - 100 + 'px';
		cube.style.top = clientHeight - 50 + 'px';
	}
}

function refreshIframe() {
	/*
	 * if (inIframe()){ refreshIframe();}
	 */
	if (srcRefresh == false) {
		var iframe = window.top.document.getElementById('embedded_odoo_plm_webgl');
		if (iframe) {
			iframe.src = iframe.src;
		}
		srcRefresh = true;
	}
};

function getElementByXpath(path, document_env) {
	return document_env.evaluate(path, document_env, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
}

// explode
/**
 * obj : the current node on the scene graph
 * box_ct_world : a vec3 center of the bounding box
 * Thank to https://stackoverflow.com/questions/46101726/how-to-explode-a-3d-model-group-in-threejs
 */
/**
 * obj : the current node on the scene graph
 * box_ct_world : a vec3 center of the bounding box
 *
 */
var _originalPositions = new Map();
var _originalBBoxCenters = new Map();
var _explosionInitialized = false;

function storeOriginalPositions() {
	_originalPositions.clear();
	_originalBBoxCenters.clear();
	for (const [guid, obj] of Object.entries(OdooCad.tree_ref_elements)) {
		_originalPositions.set(guid, obj.position.clone());
		const bbox = new THREE.Box3().setFromObject(obj);
		const bCenter = new THREE.Vector3();
		bbox.getCenter(bCenter);
		_originalBBoxCenters.set(guid, bCenter);
	}
}

function explode(obj, guid, globalCenter, speed, maxSize) {
	const originalPos = _originalPositions.get(guid);
	if (!originalPos) return;

	// Direction: from global bbox center to this object's geometric center
	const objCenter = _originalBBoxCenters.get(guid) || originalPos;
	const dir = new THREE.Vector3().subVectors(objCenter, globalCenter);

	// Fallback: part sits at center → use its bounding box center as direction
	if (dir.length() < 0.001) {
		obj.position.copy(originalPos);
		return;
	}

	// Displacement is proportional to the max dimension of the assembly
	dir.normalize().multiplyScalar((speed / 100) * maxSize);

	obj.position.set(
		originalPos.x + dir.x,
		originalPos.y + dir.y,
		originalPos.z + dir.z
	);
}



document.addEventListener('DOMContentLoaded', function () {
	init();
	initcommand();
	render();
}, false);

if (inIframe()) {
	window.top[0].document.addEventListener('DOMContentLoaded', function () {
		var carousel = parent.document.getElementById('o-carousel-product');
		if (carousel) {
			var iframe = parent.document.getElementById('embedded_odoo_plm_webgl');
			var title = document.querySelector("#odoo_plm_title");
			if (title) {
				title.style.height = '0.01px';
				title.style.border = '1px solid white';
				title.children[0].remove;
			}
			var refreshed = iframe.getAttribute('o-plm-refreshed');
			if (refreshed == 'false' || refreshed == null) {
				carousel.addEventListener("click", function () {
					console.log("refreshed");
					refreshIframe();
				})
				iframe.setAttribute('o-plm-refreshed', true);
			}
		}
	}, false);

}
// commandEffects();

const defined_orientation = {
	TOP: {
		offsetFactor: {
			x: 0,
			y: 0,
			z: 1,
		},
		axisAngle: {
			x: 0,
			y: 0,
			z: 0,
		},
	},

	BOTTOM: {
		offsetFactor: {
			x: 0,
			y: 0,
			z: -1,
		},
		axisAngle: {
			x: Math.PI,
			y: 0,
			z: 0,
		},
	},

	FRONT: {
		offsetFactor: {
			x: 0,
			y: -1,
			z: 0,
		},
		axisAngle: {
			x: Math.PI / 2,
			y: 0,
			z: 0,
		},
	},

	BACK: {
		offsetFactor: {
			x: 0,
			y: 1,
			z: 0,
		},
		axisAngle: {
			x: -(Math.PI / 2),
			y: 0,
			z: Math.PI,
		},
	},

	LEFT: {
		offsetFactor: {
			x: -1,
			y: 0,
			z: 0,
		},
		axisAngle: {
			x: Math.PI / 2,
			y: -(Math.PI / 2),
			z: 0,
		},
	},

	RIGHT: {
		offsetFactor: {
			x: 1,
			y: 0,
			z: 0,
		},
		axisAngle: {
			x: Math.PI / 2,
			y: Math.PI / 2,
			z: 0,
		},
	}
};

export { camera };
export { tweenCamera };
