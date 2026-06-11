// Some of the code here is taken from
// https://github.com/leemun1/three-viewcube
// thanks https://github.com/leemun1

import * as THREE from "./lib/three.js/build/three.module.js";
import * as ODOOCAD from "./lib/odoocad/odoocad.js";
// Controls
import {OrbitControls} from "./lib/three.js/examples/jsm/controls/OrbitControls.js";
import Stats from "./lib/three.js/examples/jsm/libs/stats.module.js";
import {
    CSS2DObject,
    CSS2DRenderer,
} from "./lib/three.js/examples/jsm/renderers/CSS2DRenderer.js";

var debug_3d = false;
let OdooCad;
let cube;
let clicked = false;
const ODOO_COLOR = "#714B67";
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
var aspect = 2; // The canvas default

var mesure_items = [];
var snapDistance = 2;
var sphereHelper;
var sphereHelperDiv;
let ctrlDown = false;
const pointer = new THREE.Vector2();
const last_highlighted_li = null;
const last_highlighted_part = null;
const ODOO_HILIGHT_COLOR = new THREE.Color("#eda3da");

function createSphereHelper() {
    var sphere = new THREE.SphereGeometry(snapDistance, snapDistance, snapDistance);
    sphere.widthSegments = 32;
    sphere.heightSegments = 32;
    const material = new THREE.MeshBasicMaterial({color: 0xffff00});
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
    const fitHeightDistance = maxSize / (2 * Math.atan((Math.PI * camera.fov) / 360));
    const fitWidthDistance = fitHeightDistance / camera.aspect;
    const distance = fitOffset * Math.max(fitHeightDistance, fitWidthDistance);
    const direction = controls.target
        .clone()
        .sub(camera.position)
        .normalize()
        .multiplyScalar(distance);
    controls.minDistance = 0.01;
    controls.maxDistance = distance * 10;
    controls.target.copy(center);
    camera.near = distance / 100;
    camera.far = distance * 100;
    scene.fog.near = camera.far;
    scene.fog.far = camera.far * 10;
    camera.updateProjectionMatrix();
    camera.position.copy(controls.target).sub(direction);
    resetLight(box, maxSize);
    sphereHelper.scale.set(maxSize / 100, maxSize / 100, maxSize / 100);
    controls.update();
    render();
}

function addAmbient() {
    addCamera();
    addLight();
    addOrbit();
    /* Add gradient background */
    scene.background = new THREE.Color(0xe0e0e0);
    scene.fog = new THREE.Fog(0xe0e0e0, 200, 1000);
    // Ground
    tecnicalBckground();
}

function togleBackgound() {
    if (togleBackgoundV) {
        togleBackgoundV = false;
        tecnicalBckground();
    } else {
        togleBackgoundV = true;
        imageBckground("/plm_web_3d/static/src/img/bakgroung_360/room.jpg");
    }
}

function tecnicalBckground() {
    objectAxesHelper.visible = true;
    planeMeshFloar = new THREE.Mesh(
        new THREE.PlaneGeometry(2000, 2000),
        new THREE.MeshPhongMaterial({
            color: 0x999999,
            depthWrite: false,
            transparent: true,
            opacity: 0.15,
        })
    );
    planeGrid = new THREE.GridHelper(200, 40, 0x000000, 0x000000);
    planeMeshFloar.rotation.x = -Math.PI / 2;
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
        case "tecnical":
            tecnicalBckground();
            break;
        case "room1":
            imageBckground("/plm_web_3d/static/src/img/bakgroung_360/room.jpg");
            break;
        case "room2":
            imageBckground("/plm_web_3d/static/src/img/bakgroung_360/white_room.png");
            break;
        case "workshop1":
            imageBckground("/plm_web_3d/static/src/img/bakgroung_360/workshop1.png");
            break;
        case "workshop2":
            imageBckground("/plm_web_3d/static/src/img/bakgroung_360/workshop2.png");
            break;
        case "workshop3":
            imageBckground("/plm_web_3d/static/src/img/bakgroung_360/workshop3.png");
            break;
        case "outdoor":
            imageBckground("/plm_web_3d/static/src/img/bakgroung_360/outdoor.png");
            break;
        default:
            tecnicalBckground();
    }
};

function imageBckground(path_to_load) {
    objectAxesHelper.visible = false;
    const loader = new THREE.TextureLoader();
    planeGrid.visible = false;
    planeMeshFloar.visible = false;
    const texture = loader.load(path_to_load, () => {
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
    const measurementDiv = document.createElement("div");
    const labelDiv = document.createElement("div");
    const close_button = document.createElement("button");
    close_button.type = "button";
    close_button.innerHTML = "x";
    close_button.id = lineId;
    close_button.className = "measurementButton";
    measurementDiv.className = "measurement";
    labelDiv.className = "measurementLabel";
    labelDiv.innerText = "0.0 mm";
    measurementDiv.appendChild(labelDiv);
    measurementDiv.appendChild(close_button);
    // Remove the lable from scene
    close_button.addEventListener("pointerdown", function () {
        console.log("remove");
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
    new_material.color.setHex("#000000");
    new_point.material = new_material;
    scene.add(new_point);
    return new_point;
}

function show_all_scene_item() {
    var i;
    var tree_item_visibility = document.getElementsByClassName("tree_item_visibility");
    for (i = 0; i < tree_item_visibility.length; i++) {
        var icon = tree_item_visibility[i];
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    }
    OdooCad.show_all();
}

function hide_all_scene_item() {
    var i;
    var tree_item_visibility = document.getElementsByClassName("tree_item_visibility");
    for (i = 0; i < tree_item_visibility.length; i++) {
        var icon = tree_item_visibility[i];
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    }
    OdooCad.hide_all();
}

function init() {
    /*
     * Init function with basic definition
     */
    canvas = document.getElementById("odoo_canvas");
    const main_3d_web = document.getElementById("main_3d_web");
    aspect = canvas.clientWidth / canvas.clientHeight;
    renderer = new THREE.WebGLRenderer({
        canvas,
        preserveDrawingBuffer: true,
    });
    renderer.gammaInput = true;
    renderer.gammaOutput = true;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap; // Default
    // THREE.PCFShadowMap
    /*
     * Label Renderer
     */
    var bounding_ret = canvas.getBoundingClientRect();
    labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(canvas.clientWidth, canvas.clientHeight);
    labelRenderer.domElement.style.position = "absolute";
    labelRenderer.domElement.style.top = bounding_ret.y;
    labelRenderer.domElement.style.pointerEvents = "none";
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
    objectAxesHelper = new THREE.AxesHelper(500);
    scene.add(objectAxesHelper);
    addAmbient();
    createSphereHelper();
    //
    // load cube from html
    //
    cube = document.querySelector(".cube");
    //
    // Load document
    //
    var document_id = document
        .querySelector("#active_model")
        .getAttribute("active_model");
    var document_name = document
        .querySelector("#active_model")
        .getAttribute("document_name");
    /*
     * Inizialize OdooCAD
     */
    OdooCad = new ODOOCAD.OdooCAD(scene);
    OdooCad.load_document(document_id, document_name);
    if (document_name && document_name.split(".").pop().toLowerCase() === "dxf") {
        controls.enableRotate = false;
        if (cube) cube.style.display = "none";
        if (planeMeshFloar) planeMeshFloar.visible = false;
        if (planeGrid) planeGrid.visible = false;
        if (objectAxesHelper) objectAxesHelper.visible = false;
        [
            document.getElementById("webgl_background")?.closest(".plm_button"),
            document.getElementById("toggle_light_settings"),
            document.getElementById("light_settings_group"),
            document.getElementById("object_transparency")?.closest(".plm_button"),
            document.getElementById("color_object_grp")?.closest(".plm_button"),
            document.getElementById("plm_button1"),
        ].forEach((el) => {
            if (el) el.style.display = "none";
        });
    }
    /*
     * Inizialize tree view search
     */
    // Commented the above as there is no id in the document with
    // input_search_document_tree present.
    //  var input_document_tree = document.getElementById('input_search_document_tree');
    var input_document_list = document.getElementById("input_search_document_list");
    console.log("hel ....... oo .........cad called ");
    input_document_list.addEventListener("keyup", OdooCad.search_document_tree);
    /*
     * Function to hide show all components
     */
    var bnt_hide_all_parts = document.getElementById("hide_all_parts");
    bnt_hide_all_parts.addEventListener("click", hide_all_scene_item);

    var bnt_show_all_parts = document.getElementById("show_all_parts");
    bnt_show_all_parts.addEventListener("click", show_all_scene_item);
}

function getCameraCSSMatrix(matrix) {
    var elements = matrix.elements;

    return (
        "matrix3d(" +
        epsilon(elements[0]) +
        "," +
        epsilon(-elements[1]) +
        "," +
        epsilon(elements[2]) +
        "," +
        epsilon(elements[3]) +
        "," +
        epsilon(elements[4]) +
        "," +
        epsilon(-elements[5]) +
        "," +
        epsilon(elements[6]) +
        "," +
        epsilon(elements[7]) +
        "," +
        epsilon(elements[8]) +
        "," +
        epsilon(-elements[9]) +
        "," +
        epsilon(elements[10]) +
        "," +
        epsilon(elements[11]) +
        "," +
        epsilon(elements[12]) +
        "," +
        epsilon(-elements[13]) +
        "," +
        epsilon(elements[14]) +
        "," +
        epsilon(elements[15]) +
        ")"
    );
}

function epsilon(value) {
    return Math.abs(value) < 1e-10 ? 0 : value;
}

function initcommand() {
    function bindEl(id, event, fn) {
        const el = document.getElementById(id);
        if (el) el[event] = fn;
    }
    function bindElEvent(id, event, fn) {
        const el = document.getElementById(id);
        if (el) el.addEventListener(event, fn);
    }

    bindEl("webgl_background", "onchange", function (event) {
        change_background();
    });

    bindElEvent("activatorClick", "click", onActivatorClick);
    bindElEvent("click_show", "click", on_data_card_button_click);

    document.addEventListener("pointerdown", onClick, false);
    document.addEventListener("pointermove", window.onPointerMove);
    document.addEventListener("keydown", onKeyDone);
    document.addEventListener("keyup", onKeyup);

    // Permanent menu delegates → real buttons
    bindEl("fit_view_perm", "onclick", function () {
        fitCameraToSelectionEvent();
    });
    bindEl("save_view_perm", "onclick", function () {
        saveAsImage();
    });
    bindEl("markup_button_perm", "onclick", function () {
        openMarkupEditor();
    });
    bindEl("show_all_perm", "onclick", function () {
        show_all_scene_item();
    });
    bindEl("measure_btn_perm", "onclick", function () {
        ctrlDown = !ctrlDown;
        drawingLine = ctrlDown;
        renderer.domElement.style.cursor = ctrlDown ? "crosshair" : "pointer";
        this.classList.toggle("active", ctrlDown);
        if (!ctrlDown) {
            scene.remove(measurementLabels[lineId]);
            scene.remove(startPoint[lineId]);
            scene.remove(endPoint[lineId]);
            scene.remove(lines[lineId]);
            lineId++;
        }
    });

    const shortcutModal = document.getElementById("shortcut_modal");
    bindEl("help_btn", "onclick", function () {
        if (shortcutModal) shortcutModal.classList.add("open");
    });
    bindEl("shortcut_modal_close", "onclick", function () {
        if (shortcutModal) shortcutModal.classList.remove("open");
    });
    if (shortcutModal) {
        shortcutModal.addEventListener("click", function (e) {
            if (e.target === shortcutModal) shortcutModal.classList.remove("open");
        });
    }

    bindElEvent("odoo_canvas", "OdooCAD_fit_items", fitCameraToSelectionEvent);

    // Light controls
    bindEl("object_distance", "oninput", chenge_light_distance);
    bindEl("object_light1", "oninput", chenge_light1);
    bindEl("object_light2", "oninput", chenge_light2);
    bindEl("object_light3", "oninput", chenge_light3);
    bindEl("object_light_camera", "oninput", chenge_light_camera);
    bindEl("object_light_ambient", "oninput", chenge_light_ambient);
    bindEl("object_transparency", "oninput", change_object_transparency);
    bindEl("object_explosion", "oninput", change_object_explosion);

    const activeModel = document.querySelector("#active_model");
    if (!activeModel) return;
    var document_id = activeModel.getAttribute("active_model");
    var xmlhttp = new XMLHttpRequest();
    var url = "../plm/get_product_info/?document_id=" + document_id;

    xmlhttp.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            var result = JSON.parse(this.responseText);
            var product_info = document.getElementById("product_info");
            if (product_info) product_info.innerHTML = result.component;
            var document_info = document.getElementById("document_info");
            if (document_info) document_info.innerHTML = result.document;
        }
    };
    xmlhttp.open("GET", url, true);
    xmlhttp.send();
}
function onActivatorClick(event) {
    const activatorDiv = document.getElementById("activatorDiv");
    const isOpen = !activatorDiv.classList.contains("d-none");
    if (isOpen) {
        activatorDiv.style.visibility = "hidden";
        activatorDiv.style.opacity = 0;
        activatorDiv.classList.add("d-none");
    } else {
        activatorDiv.style.visibility = "visible";
        activatorDiv.style.opacity = 0.95;
        activatorDiv.classList.remove("d-none");
    }
}

function on_data_card_button_click(event) {
    // Highlight the mouseover target
    const main_div = document.getElementById("main_div");
    if (clicked) {
        main_div.style.visibility = "invisible";
        main_div.style.opacity = 0;
    } else {
        main_div.style.visibility = "visible";
        main_div.style.opacity = 0.8;
    }
    clicked = !clicked;
}

function saveAsImage() {
    var imgData, imgNode;
    try {
        var document_name = document
            .querySelector("#active_model")
            .getAttribute("document_name");
        var strMime = "image/jpeg";
        imgData = renderer.domElement.toDataURL(strMime);

        saveFile(imgData.replace(strMime, strDownloadMime), document_name + ".jpg");
    } catch (e) {
        console.log(e);
        return;
    }
}

var saveFile = function (strData, filename) {
    var link = document.createElement("a");
    if (typeof link.download === "string") {
        document.body.appendChild(link); // Firefox requires the link to be
        // in the body
        link.download = filename;
        link.href = strData;
        link.click();
        document.body.removeChild(link); // Remove the link when done
    } else {
        location.replace(uri);
    }
};

var change_object_color = function (event) {
    var items = OdooCad.items;
    for (let i = 0; i < items.length; i += 1) {
        var material = items[i].material;
        material.color.setStyle(this.value);
    }
};

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
    } else {
        material.transparent = true;
        material.opacity = 0;
    }
};
var change_object_transparency = function (event) {
    var items = OdooCad.items;
    var value = this.value;
    for (let i = 0; i < items.length; i += 1) {
        var loop_item = items[i];
        loop_item.traverse(function (child_mesh) {
            if (child_mesh.type == "Mesh") {
                apply_transparency(child_mesh, value);
            }
        });
    }
};
var chenge_light_distance = function (event) {
    var value = this.value;
    change_light_position(value / 1000);
};
var chenge_light1 = function (event) {
    var value = this.value;
    light1.intensity = value / 100;
};
var chenge_light2 = function (event) {
    var value = this.value;
    light2.intensity = value / 100;
};
var chenge_light3 = function (event) {
    var value = this.value;
    light3.intensity = value / 100;
};
var chenge_light_ambient = function (event) {
    var value = this.value;
    ambientLight.intensity = value / 100;
};
var chenge_light_camera = function (event) {
    var value = this.value;
    cameraLight.intensity = value / 100;
};

/* , light2, light3, ambientLight;
var chenge_light_ambient = funciton(event){
	var value = this.value;
}*/
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
};

var fitCameraToSelectionEvent = function (e) {
    if (Object.values(OdooCad.tree_ref_elements).length > 0) {
        fitCameraToSelection(OdooCad.tree_ref_elements, 1.1);
        return;
    }
    fitCameraToSelection(OdooCad.items, 1.1);
};

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
            // Start the line
            const points = [];
            points.push(sphereHelper.position);
            points.push(sphereHelper.position.clone());
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            lines[lineId] = new THREE.LineSegments(
                geometry,
                new THREE.LineBasicMaterial({
                    color: 0x714b67, // ODOO COLOR
                    transparent: true,
                    linewidth: 2,
                    opacity: 0.75,
                })
            );
            lines[lineId].frustumCulled = false;
            const measurementLabel = new CSS2DObject(mesuraments());
            measurementLabel.position.copy(sphereHelper.position);
            measurementLabels[lineId] = measurementLabel;
            startPoint[lineId] = createMarker();
            scene.add(measurementLabels[lineId]);
            scene.add(lines[lineId]);
            drawingLine = true;
        } else {
            // Finish the line
            const positions = lines[lineId].geometry.attributes.position.array;
            const startVec = new THREE.Vector3(
                positions[0],
                positions[1],
                positions[2]
            );
            const endVec = sphereHelper.position.clone();
            positions[3] = endVec.x;
            positions[4] = endVec.y;
            positions[5] = endVec.z;
            lines[lineId].geometry.attributes.position.needsUpdate = true;
            // Update label with final distance at midpoint
            const dist = startVec.distanceTo(endVec);
            const mid = new THREE.Vector3()
                .addVectors(startVec, endVec)
                .multiplyScalar(0.5);
            if (measurementLabels[lineId]) {
                measurementLabels[lineId].position.copy(mid);
                const lbl = measurementLabels[lineId].element.querySelector(
                    ".measurementLabel"
                );
                if (lbl) lbl.innerText = dist.toFixed(2) + " mm";
            }
            endPoint[lineId] = createMarker();
            drawingLine = false;
            lineId++;
        }
    }
};

/**
 * OdooCADApplication.js
 * Final Version: Deep Search & Forced Container Scroll
 */

// 1. GLOBAL STATE & SAFETY
if (typeof window.last_highlighted_li === "undefined") {
    window.last_highlighted_li = null;
}
if (typeof window.last_highlighted_sidebar_el === "undefined") {
    window.last_highlighted_sidebar_el = null;
}
window.ODOO_HILIGHT_COLOR = new THREE.Color("#eda3da");
window.tooltipCache = {};
window.tooltipTimer = null;
window.tooltipPendingGuid = null;

// Helper to expand all parent folders in the sidebar tree
function expandAncestors(element) {
    let parent = element.parentElement;
    while (parent && parent.id !== "document_tree") {
        if (parent.tagName === "UL" && parent.classList.contains("nested")) {
            parent.classList.add("active");
            // Find the toggler span (caret) on the previous sibling or parent LI
            const li = parent.closest("li");
            if (li) {
                const caret = li.querySelector(".caret");
                if (caret) caret.classList.add("caret-down");
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
            if (!child.getObjectByName("__highlight_edges__")) {
                const edges = new THREE.EdgesGeometry(child.geometry);
                const edgeMat = new THREE.LineBasicMaterial({color: 0x714b67});
                const wireframe = new THREE.LineSegments(edges, edgeMat);
                wireframe.name = "__highlight_edges__";
                wireframe.raycast = () => {};
                child.add(wireframe);
            }
        } else {
            if (child.material.userData.originalColor) {
                child.material.color.copy(child.material.userData.originalColor);
            }
            const wireframe = child.getObjectByName("__highlight_edges__");
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
    if (typeof canvas === "undefined" || !canvas) return;
    if (typeof raycaster === "undefined" || typeof camera === "undefined") return;

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
                const nodeName = (obj.name || "").toLowerCase();
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
    const tooltip = document.getElementById("part_tooltip");
    if (!tooltip) {
        console.warn("Tooltip element #part_tooltip not found in DOM");
    } else if (hoveredGuid) {
        // Always track cursor so the tooltip appears at the right position when it shows
        tooltip.style.left = event.clientX + 15 + "px";
        tooltip.style.top = event.clientY + 15 + "px";

        if (hoveredGuid !== window.tooltipPendingGuid) {
            // Moved to a new object — hide any visible tooltip and restart the delay
            tooltip.style.display = "none";
            tooltip.innerText = "";
            clearTimeout(window.tooltipTimer);
            window.tooltipPendingGuid = hoveredGuid;

            window.tooltipTimer = setTimeout(function () {
                const guid = window.tooltipPendingGuid;
                if (!guid) return;
                tooltip.style.display = "block";

                const obj3d = OdooCad.tree_ref_elements[guid];
                if (obj3d) {
                    const srcName =
                        (obj3d.userData && obj3d.userData.engineering_code) ||
                        obj3d.name ||
                        obj3d.type ||
                        "Component";

                    if (window.tooltipCache[srcName]) {
                        tooltip.innerText = window.tooltipCache[srcName];
                    } else {
                        tooltip.innerText = srcName;

                        const parentId =
                            document
                                .getElementById("main_3d_web")
                                ?.getAttribute("data-res-id") ||
                            document
                                .getElementById("active_model")
                                ?.getAttribute("active_model") ||
                            "";
                        const url = `/plm/get_3d_web_document_info/?src_name=${encodeURIComponent(
                            srcName
                        )}&parent_id=${parentId}`;
                        fetch(url)
                            .then((response) => response.text())
                            .then((data) => {
                                const finalMsg = data.trim() || srcName;
                                window.tooltipCache[srcName] = finalMsg;
                                if (window.tooltipPendingGuid === guid) {
                                    tooltip.innerText = finalMsg;
                                }
                            })
                            .catch((err) => {
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
        tooltip.style.display = "none";
        tooltip.innerText = "";
    }

    // --- HIGHLIGHT SYNC LOGIC ---
    if (hoveredGuid !== window.last_highlighted_li) {
        if (window.last_highlighted_li) {
            window.highlight3D(window.last_highlighted_li, false);
        }

        if (window.last_highlighted_sidebar_el) {
            const el = window.last_highlighted_sidebar_el;
            el.classList.remove("document_tree_line_highlighted");
            el.style.backgroundColor = "";
            el.style.color = "";
            el.style.border = "";
            el.style.boxShadow = "";
            const children = el.querySelectorAll("span, i");
            children.forEach((c) => {
                c.style.backgroundColor = "";
                c.style.color = "";
            });
            window.last_highlighted_sidebar_el = null;
        }

        if (hoveredGuid) {
            window.highlight3D(hoveredGuid, true);
            let targetLi = document.querySelector(
                `li[webgl_ref_name="${hoveredGuid}"]`
            );
            if (!targetLi) {
                const span = document.querySelector(
                    `span[webgl_ref_name="${hoveredGuid}"]`
                );
                if (span) targetLi = span.closest("li");
            }

            if (targetLi) {
                const highlightColor = "#eda3da";
                const textColor = "#000000";
                expandAncestors(targetLi);
                targetLi.classList.add("document_tree_line_highlighted");
                targetLi.style.setProperty(
                    "background-color",
                    highlightColor,
                    "important"
                );
                targetLi.style.setProperty("color", textColor, "important");
                targetLi.style.setProperty("border", "2px solid #714B67", "important");
                targetLi.style.setProperty(
                    "box-shadow",
                    "0 0 14px rgba(113, 75, 103, 0.7)",
                    "important"
                );
                targetLi.style.borderRadius = "4px";
                window.last_highlighted_sidebar_el = targetLi;

                const subElements = targetLi.querySelectorAll("span, i");
                subElements.forEach((sub) => {
                    sub.style.setProperty(
                        "background-color",
                        highlightColor,
                        "important"
                    );
                    sub.style.setProperty("color", textColor, "important");
                });

                targetLi.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                    inline: "nearest",
                });
            }
        }
        window.last_highlighted_li = hoveredGuid;
    }
    if (typeof render === "function") render();
};

// 4. ATTACH EVENT LISTENER SAFELY
// Remove existing listener first to prevent multiple triggers if script reloads
document.removeEventListener("pointermove", window.onPointerMove);
document.addEventListener("pointermove", window.onPointerMove);

function onKeyDone(event) {
    if (event.key === "Control") {
        ctrlDown = true;
        drawingLine = true;
        renderer.domElement.style.cursor = "crosshair";
        document.getElementById("measure_btn_perm")?.classList.add("active");
    }
    const tag = (event.target || document.activeElement || {}).tagName || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (event.key === "f" || event.key === "F") {
        fitCameraToSelectionEvent();
    }
    if (event.key === "a" || event.key === "A") {
        show_all_scene_item();
        render();
    }
    if (event.key === "h" || event.key === "H") {
        const guid = window.last_highlighted_li;
        if (guid && OdooCad?.tree_ref_elements?.[guid]) {
            const obj = OdooCad.tree_ref_elements[guid];
            const show = !obj.visible;
            obj.visible = show;
            // Sync sidebar eye icon
            let targetLi = document.querySelector(`li[webgl_ref_name="${guid}"]`);
            if (!targetLi) {
                const span = document.querySelector(`span[webgl_ref_name="${guid}"]`);
                if (span) targetLi = span.closest("li");
            }
            if (targetLi) {
                const icon = targetLi.querySelector(".tree_item_visibility");
                if (icon) {
                    icon.classList.toggle("fa-eye", show);
                    icon.classList.toggle("fa-eye-slash", !show);
                }
            }
            if (!show) {
                // Remove highlight/edges when hiding; keep last_highlighted_li so a
                // second h-press (without moving the mouse) can toggle it back
                window.highlight3D(guid, false);
            }
            render();
        }
    }
}

function onKeyup(event) {
    if (event.key === "Control") {
        ctrlDown = false;
        drawingLine = false;
        renderer.domElement.style.cursor = "pointer";
        document.getElementById("measure_btn_perm")?.classList.remove("active");
        scene.remove(measurementLabels[lineId]);
        scene.remove(startPoint[lineId]);
        scene.remove(endPoint[lineId]);
        scene.remove(lines[lineId]);
        lineId++;
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
    camera = new THREE.PerspectiveCamera(fov, aspect, near, far);
    camera.position.z = 2;
    // Light
    cameraLight = new THREE.PointLight(0xffffff, 0.5);
    camera.add(cameraLight);
    scene.add(camera);
}

function addOrbit() {
    controls = new OrbitControls(camera, renderer.domElement);
    controls.addEventListener("change", render);
    controls.minDistance = 2;
    controls.maxDistance = 10;
    controls.rotateSpeed = 0.5;
    controls.target.set(0, 0, -0.2);
    controls.update();
}

function resetLight(bbox, size) {
    bbox_center = new THREE.Vector3();
    bbox.getCenter(bbox_center);
    change_light_position(size);
}

function change_light_position(size) {
    var mult = size * 1000;
    //
    var x = bbox_center.x + mult;
    var y = bbox_center.y + mult;
    var z = bbox_center.z + mult;
    //
    light1.position.z = z;
    light1.position.y = -y;
    light1.position.x = -x;
    //
    light2.position.z = z;
    light2.position.x = -x;
    light2.position.y = y;
    //
    light3.position.z = z;
    light3.position.x = x;
    light3.position.y = -y;
}

function addLight() {
    const sphereSize = 20;
    const group = new THREE.Group();
    scene.add(group);

    light1 = new THREE.SpotLight(0xf7d962, 0.1);
    light1.castShadow = true; // Default false
    light1.position.z = 70;
    light1.position.y = -70;
    light1.position.x = -70;
    light1.intensity = 0.5;
    scene.add(light1);

    light2 = new THREE.SpotLight(0xffdddd, 0.1);
    light2.castShadow = true; // Default false
    light2.position.z = 70;
    light2.position.x = -70;
    light2.position.y = 70;
    light2.intensity = 0.5;
    scene.add(light2);

    light3 = new THREE.SpotLight(0xf7d962, 0.1);
    light3.castShadow = true; // Default false
    light3.position.z = 70;
    light3.position.x = 70;
    light3.position.y = -70;
    light3.intensity = 0.5;
    scene.add(light3);

    ambientLight = new THREE.HemisphereLight(
        "#b199ff", // Bright sky color
        "darkslategrey", // Dim ground color
        0.5 // Intensity
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
        var intersection = intersections.length > 0 ? intersections[0] : null;
        if (intersection !== null) {
            var first = true;
            var nearestPoint = new THREE.Vector3();
            var check_distance;
            var distance;
            var vertices = intersection.object.geometry.attributes.position.array;
            for (let i = 0; i < vertices.length; i += 3) {
                var spoolVector = new THREE.Vector3();
                spoolVector.x = vertices[i] + intersection.object.position.x;
                spoolVector.y = vertices[i + 1] + intersection.object.position.y;
                spoolVector.z = vertices[i + 2] + intersection.object.position.z;
                check_distance = intersection.point.distanceTo(spoolVector);
                if (first) {
                    distance = check_distance;
                    nearestPoint = spoolVector;
                    first = false;
                } else if (check_distance < distance) {
                    distance = check_distance;
                    nearestPoint = spoolVector;
                    /*
                     * Console.log(distance); console.log("IP",
                     * intersection.point); console.log("SV", spoolVector);
                     * console.log("NP", nearestPoint);
                     */
                }
            }
            sphereHelper.position.copy(nearestPoint);
            sphereHelper.visible = true;
            // Live preview while drawing a measurement line
            if (drawingLine && lines[lineId]) {
                const pos = lines[lineId].geometry.attributes.position.array;
                pos[3] = nearestPoint.x;
                pos[4] = nearestPoint.y;
                pos[5] = nearestPoint.z;
                lines[lineId].geometry.attributes.position.needsUpdate = true;
                const startVec = new THREE.Vector3(pos[0], pos[1], pos[2]);
                const liveDist = startVec.distanceTo(nearestPoint);
                const liveMid = new THREE.Vector3()
                    .addVectors(startVec, nearestPoint)
                    .multiplyScalar(0.5);
                if (measurementLabels[lineId]) {
                    measurementLabels[lineId].position.copy(liveMid);
                    const lbl = measurementLabels[lineId].element.querySelector(
                        ".measurementLabel"
                    );
                    if (lbl) lbl.innerText = liveDist.toFixed(2) + " mm";
                }
            }
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
}

function tweenCamera(position) {
    controls.target = new THREE.Vector3(0, 0, 0);
    console.log(position);
    const {offsetFactor, axisAngle} = defined_orientation[position];
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
    camera.position.set(offset.x, offset.y, offset.z);
    // Controls.update();
    fitCameraToSelection(OdooCad.tree_ref_elements, 1.1);
    // Render();
}

function resizeCanvasToDisplaySize() {
    canvas = renderer.domElement;
    // Look up the size the canvas is being displayed
    const clientWidth = canvas.clientWidth;
    const clientHeight = canvas.clientHeight;
    // Adjust displayBuffer size to match
    if (canvas.width !== clientWidth || canvas.height !== clientHeight) {
        // You must pass false here or three.js sadly fights the browser
        camera.aspect = clientWidth / clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(clientWidth, clientHeight);
        labelRenderer.setSize(clientWidth, clientHeight);
    }
    if (cube) {
        cube.style.left = clientWidth - 100 + "px";
        cube.style.top = clientHeight - 50 + "px";
    }
}

function refreshIframe() {
    /*
     * If (inIframe()){ refreshIframe();}
     */
    if (srcRefresh == false) {
        var iframe = window.top.document.getElementById("embedded_odoo_plm_webgl");
        if (iframe) {
            iframe.src = iframe.src;
        }
        srcRefresh = true;
    }
}

function getElementByXpath(path, document_env) {
    return document_env.evaluate(
        path,
        document_env,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
    );
}

// Explode
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

document.addEventListener(
    "DOMContentLoaded",
    function () {
        init();
        initcommand();
        render();
    },
    false
);

if (inIframe()) {
    window.top[0].document.addEventListener(
        "DOMContentLoaded",
        function () {
            var carousel = parent.document.getElementById("o-carousel-product");
            if (carousel) {
                var iframe = parent.document.getElementById("embedded_odoo_plm_webgl");
                var title = document.querySelector("#odoo_plm_title");
                if (title) {
                    title.style.height = "0.01px";
                    title.style.border = "1px solid white";
                    title.children[0].remove;
                }
                var refreshed = iframe.getAttribute("o-plm-refreshed");
                if (refreshed == "false" || refreshed == null) {
                    carousel.addEventListener("click", function () {
                        console.log("refreshed");
                        refreshIframe();
                    });
                    iframe.setAttribute("o-plm-refreshed", true);
                }
            }
        },
        false
    );
}
// CommandEffects();

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
    },
};

export {camera};
export {tweenCamera};
