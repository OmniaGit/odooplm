// some of the code here is taken from
// https://github.com/leemun1/three-viewcube
// thanks https://github.com/leemun1

import * as THREE from './lib/three.js/build/three.module.js';
import * as ODOOCAD from './lib/odoocad/odoocad.js';
// controls
import { OrbitControls } from './lib/three.js/examples/jsm/controls/OrbitControls.js';
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
let last_highlighted_li = null;
let last_highlighted_part = null;
const ODOO_HILIGHT_COLOR = new THREE.Color("#eda3da");

function createSphereHelper() {
	var sphere = new THREE.SphereGeometry(snapDistance,
		snapDistance,
		snapDistance);
	sphere.widthSegments = 32;
	sphere.heightSegments = 32;
	const material = new THREE.MeshBasicMaterial({ color: 0xffff00 });
	sphereHelper = new THREE.Mesh(sphere, material);
	sphereHelper.visible = false;
	scene.add(sphereHelper);
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
	sphereHelper.scale.set(maxSize / 100, maxSize / 100, maxSize / 100)
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
		new THREE.MeshPhongMaterial({ color: 0x999999, depthWrite: false }));
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
		default:
			tecnicalBckground();

	}
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

    close_button.addEventListener('pointerdown', function () {
        scene.remove(measurementLabels[close_button.id]);
        scene.remove(endPoint[close_button.id]);
        scene.remove(startPoint[close_button.id]);
        scene.remove(lines[close_button.id]);
    });

    return measurementDiv;
}

function createMarker() {
	var new_point = sphereHelper.clone();
	var new_material = new_point.material.clone();
	new_material.color.setHex('#000000');
	new_point.material = new_material;
	scene.add(new_point);
	return new_point
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
	var element = document.getElementById("fit_view");
	element.onclick = function (event) {
		fitCameraToSelectionEvent();
		/*		fitCameraToSelection(OdooCad.tree_ref_elements,
									 1.1);
			*/
	}
	var selector = document.getElementById("webgl_background");
	selector.onchange = function (event) {
		change_background();
	}

	let click_show = document.getElementById("click_show");
	let activatorClick = document.getElementById("activatorClick");
	activatorClick.addEventListener("click", onActivatorClick);

	click_show.addEventListener("click", on_data_card_button_click);

	// document.addEventListener('mousemove', onDocumentMousemove, false);
	document.addEventListener('pointerdown', onClick, false);
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

	const html_canvas = document.getElementById('odoo_canvas');
	html_canvas.addEventListener("OdooCAD_fit_items", fitCameraToSelectionEvent, false);
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
	 * Make screen shot
	 */
	document.getElementById("save_view").addEventListener('click', saveAsImage);
	/*
	 * Load datacard
	 */
	var document_id = document.querySelector('#active_model').getAttribute('active_model');
	const url = `/plm/get_product_info?document_id=${document_id}`;

    fetch(url)
        .then(res => res.json())
        .then(function (result) {
            if (result.error) {
                console.error("Server Error:", result.error);
                return;
            }

            let product_info = document.getElementById("product_info");
            let document_info = document.getElementById("document_info");

            product_info.innerHTML = (result.component || []).join("");
            document_info.innerHTML = result.document || "";
        })
        .catch(function (err) {
            console.error("Fetch Error:", err);
        });
}
function onActivatorClick(event) {
	// highlight the mouseover target
	let activatorDiv = document.getElementById("activatorDiv");
	let permanentMenu = document.getElementById("dropdown_menu_left_permenant");
	let main_command_slide = document.getElementById('mainCommandSlide')
	//    $(bottom_command).toggleClass('d-none')
	if (activatorDiv.classList.contains('d-none')) {
		permanentMenu.style.display = 'none';
		activatorDiv.style.visibility = 'visible';
		activatorDiv.style.opacity = 0.8;
		activatorDiv.classList.remove('d-none');
		main_command_slide.style.height = '210px';
	}
	else {
		permanentMenu.style.display = 'block';
		activatorDiv.style.visibility = 'invisible';
		activatorDiv.style.opacity = 0;
		activatorDiv.classList.add('d-none');
		main_command_slide.style.height = '26px';
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

var change_object_color = function (event) {
	var items = OdooCad.items;
	for (let i = 0; i < items.length; i = i + 1) {
		var material = items[i].material;
		material.color.setStyle(this.value);
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

/*, light2, light3, ambientLight;
var chenge_light_ambient = funciton(event){
	var value = this.value;
}*/
var change_object_explosion = function (event) {
	var entitys_BBOX = OdooCad.active_bbox;
	var center = new THREE.Vector3();
	var value = parseFloat(this.value);
	var factor = entitys_BBOX.max.length() / 20000;

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

	entitys_BBOX.getCenter(center);

	// Explode each named tree item independently
	for (const [guid, obj] of Object.entries(OdooCad.tree_ref_elements)) {
		explode(obj, guid, center, value, factor);
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
				color: 0x714B67,  // ODOO COLOR
				transparent: true,
				linewidth: 2,
				opacity: 0.75
			}));
			lines[lineId].frustumCulled = false;
			const measurementLabel = new CSS2DObject(mesuraments());
			measurementLabel.position.copy(sphereHelper.position);
			measurementLabels[lineId] = measurementLabel;
			startPoint[lineId] = createMarker();
			scene.add(measurementLabels[lineId]);
			scene.add(lines[lineId]);
			drawingLine = true;
		}
		else {
			// finish the line
			const positions = lines[lineId].geometry.attributes.position.array;
			positions[3] = sphereHelper.position.x;
			positions[4] = sphereHelper.position.y;
			positions[5] = sphereHelper.position.z;
			lines[lineId].geometry.attributes.position.needsUpdate = true;
			endPoint[lineId] = createMarker();
			drawingLine = false;
			lineId++;
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
		if (child instanceof THREE.Mesh && child.material) {
			if (enable) {
				if (!child.material.userData.originalColor) {
					child.material.userData.originalColor = child.material.color.clone();
				}
				child.material.color.copy(window.ODOO_HILIGHT_COLOR);
			} else if (child.material.userData.originalColor) {
				child.material.color.copy(child.material.userData.originalColor);
			}
		}
	});
	if (typeof render === "function") render();
};


window.onPointerMove = function (event) {
	if (typeof canvas === 'undefined' || !canvas) return;
	if (typeof raycaster === 'undefined' || typeof camera === 'undefined') return;

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
		tooltip.style.display = 'block';
		tooltip.style.left = (event.clientX + 15) + 'px';
		tooltip.style.top = (event.clientY + 15) + 'px';

		const obj3d = OdooCad.tree_ref_elements[hoveredGuid];
		if (obj3d) {
			const srcName = (obj3d.userData && obj3d.userData.engineering_code) || obj3d.name || obj3d.type || "Component";

			if (window.tooltipCache[srcName]) {
				tooltip.innerText = window.tooltipCache[srcName];
			} else {
				tooltip.innerText = srcName;

				const parentId = document.getElementById('main_3d_web')?.getAttribute('data-res-id') || document.getElementById('active_model')?.getAttribute('active_model') || "";
				const url = `/plm/get_3d_web_document_info/?src_name=${encodeURIComponent(srcName)}&parent_id=${parentId}`;
				fetch(url)

					.then(response => response.text())
					.then(data => {
						const finalMsg = data.trim() || srcName;
						window.tooltipCache[srcName] = finalMsg;
						if (window.last_highlighted_li === hoveredGuid) {
							tooltip.innerText = finalMsg;
						}
					})
					.catch(err => {
						console.error("Tooltip error:", err);
						window.tooltipCache[srcName] = srcName;
						tooltip.innerText = srcName;
					});
			}
		} else {
			tooltip.innerText = "Unknown Part";
		}
	} else {
		tooltip.style.display = 'none';
		tooltip.innerText = "";
	}


	// --- HIGHLIGHT SYNC LOGIC ---
	// ✅ PERSISTENT HIGHLIGHT: Only change highlight if we hit a NEW part.
	// We no longer clear it when moving into empty space (hoveredGuid === null).
	if (hoveredGuid && hoveredGuid !== window.last_highlighted_li) {
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

    if (drawingLine && lines[lineId]) {
    const line = lines[lineId];
    const positions = line.geometry.attributes.position.array;

    const current = sphereHelper.position;

    positions[3] = current.x;
    positions[4] = current.y;
    positions[5] = current.z;

    line.geometry.attributes.position.needsUpdate = true;

    // update distance label
    const start = new THREE.Vector3(
        positions[0],
        positions[1],
        positions[2]
    );

    const distance = start.distanceTo(current);

    const label = measurementLabels[lineId]?.element?.querySelector('.measurementLabel');
    if (label) {
        label.innerText = distance.toFixed(2) + " mm";
    }
}
};


// 4. ATTACH EVENT LISTENER SAFELY
// Remove existing listener first to prevent multiple triggers if script reloads
document.removeEventListener('pointermove', window.onPointerMove);
document.addEventListener('pointermove', window.onPointerMove);

function onKeyDone(event) {
	if (event.key === "Control") {
		ctrlDown = true;
		drawingLine = true;
		renderer.domElement.style.cursor = "crosshair";
	}
}


function onKeyup(event) {
	if (event.key === "Control") {
		ctrlDown = false;
		renderer.domElement.style.cursor = "pointer";
		if (drawingLine) {
			drawingLine = false;
		}
		function onKeyup(event) {
            if (event.key === "Control") {
                ctrlDown = false;
                renderer.domElement.style.cursor = "pointer";
            }
        }
	}
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
	light3.intensity = 0.5;
	scene.add(light3);

	ambientLight = new THREE.HemisphereLight('#b199ff',        // bright sky color
		'darkslategrey',  // dim ground color
		0.5,              // intensity
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
	if (sphereHelper) {
		raycaster.setFromCamera(pointer, camera);
		const intersections = raycaster.intersectObjects(OdooCad.items, true);
		var intersection = (intersections.length) > 0 ? intersections[0] : null;
		if (intersection !== null) {
			var first = true;
			var nearestPoint = new THREE.Vector3();
			var check_distance;
			var distance;
			var vertices = intersection.object.geometry.attributes.position.array;
			for (let i = 0; i < vertices.length; i = i + 3) {
				var spoolVector = new THREE.Vector3();
				spoolVector.x = vertices[i] + intersection.object.position.x;
				spoolVector.y = vertices[i + 1] + intersection.object.position.y;
				spoolVector.z = vertices[i + 2] + intersection.object.position.z;
				check_distance = intersection.point.distanceTo(spoolVector)
				if (first) {
					distance = check_distance;
					nearestPoint = spoolVector;
					first = false;
				} else {
					if (check_distance < distance) {
						distance = check_distance;
						nearestPoint = spoolVector;
						/*
						 * console.log(distance); console.log("IP",
						 * intersection.point); console.log("SV", spoolVector);
						 * console.log("NP", nearestPoint);
						 */
					}
				}
			}
			sphereHelper.position.copy(nearestPoint);
			sphereHelper.visible = true;
		} else {
			sphereHelper.visible = false;
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
var _explosionInitialized = false;

function storeOriginalPositions() {
	_originalPositions.clear();
	// Store positions of each NAMED tree item (Group level), not raw meshes
	for (const [guid, obj] of Object.entries(OdooCad.tree_ref_elements)) {
		_originalPositions.set(guid, obj.position.clone());
	}
}

function explode(obj, guid, box_center, speed, factor) {
	var originalPos = _originalPositions.get(guid);
	if (!originalPos) return;

	var dir = new THREE.Vector3(
		originalPos.x - box_center.x,
		originalPos.y - box_center.y,
		originalPos.z - box_center.z
	);

	// Fallback: part sits at center → use its bounding box center as direction
	if (dir.length() < 0.001) {
		var bbox = new THREE.Box3().setFromObject(obj);
		var bCenter = new THREE.Vector3();
		bbox.getCenter(bCenter);
		dir.set(
			bCenter.x - box_center.x,
			bCenter.y - box_center.y,
			bCenter.z - box_center.z
		);
	}

	if (dir.length() > 0.001) {
		dir.normalize().multiplyScalar(speed * factor * 100);
	}

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
