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
var strDownloadMime = "image/octet-stream";

const measurementLabels = {};
const endPoint={};
const startPoint={};
const lines={};
let camera, scene, canvas , renderer, labelRenderer, controls, mouse;
let planeMeshFloar, planeGrid;
let objectAxesHelper;
let raycaster ;
let light1, light2, light3;
var srcRefresh = false;
var togleBackgoundV= false;
let drawingLine = false;
let lineId = 0;
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

function createSphereHelper() {
  var sphere = new THREE.SphereGeometry(snapDistance,
		  								snapDistance,
		  								snapDistance);	
  sphere.widthSegments=32;
  sphere.heightSegments=32;
  const material = new THREE.MeshBasicMaterial( { color: 0xffff00 } );
  sphereHelper = new THREE.Mesh( sphere, material );
  sphereHelper.visible = false;
  scene.add(sphereHelper);
}

function fitCameraToSelection(selection, fitOffset = 1.2 ) {
	  const box = new THREE.Box3();
	  for( const object of selection ) box.expandByObject( object );
	  const size = box.getSize( new THREE.Vector3() );
	  const center = box.getCenter( new THREE.Vector3() );
	  const maxSize = Math.max( size.x, size.y, size.z );
	  const fitHeightDistance = maxSize / ( 2 * Math.atan( Math.PI * camera.fov / 360 ) );
	  const fitWidthDistance = fitHeightDistance / camera.aspect;
	  const distance = fitOffset * Math.max( fitHeightDistance, fitWidthDistance );
	  const direction = controls.target.clone()
	    .sub( camera.position )
	    .normalize()
	    .multiplyScalar( distance );
	  controls.minDistance = 0.01;
	  controls.maxDistance = distance * 10;
	  controls.target.copy( center );
	  camera.near = distance / 100;
	  camera.far = distance * 100;
	  scene.fog.near = camera.far
	  scene.fog.far	 = camera.far * 10
	  camera.updateProjectionMatrix();
	  camera.position.copy( controls.target ).sub(direction);
	  resetLight(box, maxSize);
	  controls.update();
	  render();
};

function addAmbient(){
	  addCamera();
	  addLight();
	  addOrbit();
	  /* add gradient background */
	  scene.background = new THREE.Color( 0xe0e0e0 );
	  scene.fog = new THREE.Fog( 0xe0e0e0, 200, 1000 );;
	  // ground
	  tecnicalBckground();
}

function togleBackgound(){
	if(togleBackgoundV){
		togleBackgoundV=false;
		tecnicalBckground();
	}
	else{
		togleBackgoundV=true;
		imageBckground('/plm_web_3d/static/src/img/bakgroung_360/room.jpg');
	}
}

function tecnicalBckground(){
	objectAxesHelper.visible=true;
	planeMeshFloar = new THREE.Mesh( new THREE.PlaneBufferGeometry( 2000, 2000 ),
			new THREE.MeshPhongMaterial( { color: 0x999999, depthWrite: false } ) );
	planeGrid = new THREE.GridHelper( 200, 40, 0x000000, 0x000000 );
	planeMeshFloar.rotation.x = - Math.PI / 2;
	scene.add( planeMeshFloar );
	planeGrid.material.opacity = 0.2;
	planeGrid.material.transparent = true;
	planeGrid.receiveShadow=true;
	scene.add( planeGrid );
	planeGrid.visible=true;
	planeMeshFloar.visible=true;
	scene.background = new THREE.Color( 0xe0e0e0 );
	render();
}

var change_background = function (){
	var value = document.getElementById("webgl_background").value;
	switch(value) {
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

function imageBckground(path_to_load){
	objectAxesHelper.visible=false;
	const loader = new THREE.TextureLoader();
	planeGrid.visible=false;
	planeMeshFloar.visible=false;
	const texture = loader.load(
			path_to_load,
	  () => {
		texture.encoding = THREE.sRGBEncoding;
		texture.mapping = THREE.EquirectangularReflectionMapping;
	    const rt = new THREE.WebGLCubeRenderTarget(texture.image.height);
	    rt.fromEquirectangularTexture(renderer, texture);
	    
	    scene.background = texture;
	    
	    const cubeCamera = new THREE.CubeCamera( 1, 100000, rt );
	    scene.add( cubeCamera );
	    
	    render();
	    controls.update();
	  });
}

function mesuraments(){
    const measurementDiv = document.createElement('div');
    const labelDiv = document.createElement('div');
    const close_button = document.createElement('button');
    close_button.type = "button";
    close_button.innerHTML ='x';
    close_button.id = lineId;
    close_button.className='measurementButton';
    measurementDiv.className = 'measurement';
    labelDiv.className = 'measurementLabel';
    labelDiv.innerText = "0.0 mm";
    measurementDiv.appendChild(labelDiv);
    measurementDiv.appendChild(close_button);
    // remove the lable from scene
    close_button.addEventListener('pointerdown', function() {
    	console.log("remove");
        scene.remove(measurementLabels[close_button.id]);
        scene.remove(endPoint[close_button.id]);
        scene.remove(startPoint[close_button.id]);
        scene.remove(lines[close_button.id]);
    });
    return measurementDiv;
}

function createMarker(){
	var new_point = sphereHelper.clone();
	var new_material = new_point.material.clone();
	new_material.color.setHex('#000000');
	new_point.material = new_material;
	scene.add(new_point);
	return new_point
}


function init() {
/*
 * init function with basic definition
 */
	const canvas =  document.getElementById('odoo_canvas');
	const main_3d_web = document.getElementById('main_3d_web');
	aspect = canvas.clientWidth/canvas.clientHeight;
	renderer = new THREE.WebGLRenderer({canvas,
										preserveDrawingBuffer: true});
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
	objectAxesHelper = new THREE.AxesHelper( 500 )
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

function epsilon( value ) {

  return Math.abs( value ) < 1e-10 ? 0 : value;

}

function initcommand(){
	var element = document.getElementById("fit_view");
	element.onclick = function(event) {
		fitCameraToSelection(OdooCad.items,
							 1.1);
	}
	var selector = document.getElementById("webgl_background");
	selector.onchange = function(event){
		change_background();
	} 
	
	let click_show = document.getElementById("click_show");
	

	click_show.addEventListener("click", on_data_card_button_click);
	
	// document.addEventListener('mousemove', onDocumentMousemove, false);
	document.addEventListener('pointerdown', onClick, false);
	document.addEventListener('pointermove', onPointerMove );
	document.addEventListener('keydown', onKeyDone);
	document.addEventListener('keyup', onKeyup);
	const html_canvas =  document.getElementById('odoo_canvas');
	html_canvas.addEventListener("OdooCAD_fit_items", fitCameraToSelectionEvent, false);
	var object_transparency = document.getElementById("object_transparency");
	object_transparency.oninput = change_object_transparency;
	
	var colorPicker = document.getElementById("object_color");
	colorPicker.oninput = change_object_color;
	/*
	 * Make screen shot
	 */
	document.getElementById("save_view").addEventListener('click', saveAsImage);
	/*
	 * Load datacard
	 */
	var document_id = document.querySelector('#active_model').getAttribute('active_model');
	var xmlhttp = new XMLHttpRequest();
	var url = "../plm/get_product_info/?document_id=" + document_id;

	xmlhttp.onreadystatechange = function() {
	    if (this.readyState == 4 && this.status == 200) {
	        var result = JSON.parse(this.responseText);
	        var product_info = document.getElementById("product_info");
	        product_info.innerHTML = result['component'];
	        var document_info = document.getElementById("document_info");
	        document_info.innerHTML = result['document'];
	    }
	};
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}

function on_data_card_button_click(event) {
	  // highlight the mouseover target
	  let main_div = document.getElementById("main_div");
	  if (clicked) {
	    console.log("not clicked");  
	    main_div.style.visibility = 'invisible';
	    main_div.style.opacity=0;
	  }
	  else{
	     console.log("clicked");  
	    main_div.style.visibility= 'visible';
	    main_div.style.opacity=0.8;
	  }
	  clicked=!clicked;
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
        
var change_object_color = function(event){
	var items = OdooCad.items;
	for (let i = 0; i < items.length; i=i+1) {
		var material = items[i].material;
		material.color.setStyle(this.value);
	}
}

var change_object_transparency = function(event) {
	var items = OdooCad.items;
	for (let i = 0; i < items.length; i=i+1) {
		var material = items[i].material;
		if(this.value>0){
			if (this.value>99.9){
				material.transparent=false;	
			} else{
				material.transparent=true;
				material.opacity = this.value/100;
			}
		}
		else{
			material.transparent=true;
			material.opacity=0;
			
		}
	}
}

var fitCameraToSelectionEvent = function(e){
	fitCameraToSelection(OdooCad.items,1.1);	
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
	if(ctrlDown){
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

function onPointerMove( event ) {
	if(canvas){
		var bounding_ret = canvas.getBoundingClientRect();
		var x = event.clientX - bounding_ret.x;
		var y = event.clientY - bounding_ret.y;
		pointer.x = (  x / canvas.clientWidth ) * 2 - 1;
		pointer.y = - ( y / canvas.clientHeight ) * 2 + 1;
		var line = lines[lineId];
		if(line){
	        const positions = line.geometry.attributes.position.array;
	        const v0 = new THREE.Vector3(positions[0],
	        							 positions[1],
	        							 positions[2]);
	        const v1 = new THREE.Vector3(sphereHelper.position.x,
	        							 sphereHelper.position.y,
	        							 sphereHelper.position.z);
	        positions[3] = sphereHelper.position.x;
	        positions[4] = sphereHelper.position.y;
	        positions[5] = sphereHelper.position.z;1
	        line.geometry.attributes.position.needsUpdate = true;
	        const distance = v0.distanceTo(v1);
	        if(measurementLabels[lineId]){
		        // measurementLabels[lineId].element.innerText =
				// distance.toFixed(2) + " mm ";
	        	measurementLabels[lineId].element.firstElementChild.innerText = distance.toFixed(2) + " mm ";
		        measurementLabels[lineId].position.lerpVectors(v0, v1, .5);
	        }
		}
		render();
		
	}
}

function onKeyDone(event) {
    if (event.key === "Control") {
        ctrlDown = true;
        drawingLine=true;
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
        scene.remove(measurementLabels[lineId]);
        scene.remove(startPoint[lineId]);
        scene.remove(endPoint[lineId]);
        scene.remove(lines[lineId]);
        lineId++;
    }
}

function inIframe () {
    try {
        return window.self !== window.top;
    } catch (e) {
        return true;
    }
}

function addCamera(){
	camera = new THREE.PerspectiveCamera(fov,
			aspect,
			near,
			far);
	camera.position.z = 2;
	var light = new THREE.PointLight(0xffffff, 1, Infinity);
	camera.add(light);
}

function addOrbit(){
	controls = new OrbitControls( camera, renderer.domElement );
	controls.addEventListener('change', render ); 
	controls.minDistance = 2;
	controls.maxDistance = 10;
	controls.rotateSpeed = 0.5
	controls.target.set( 0, 0, - 0.2 );
	controls.update();
}

function resetLight(bbox, size) {
	var mult = size * 1000;
	var center = new THREE.Vector3(); 
	bbox.getCenter(center);
	var x = center.x + mult;
	var y = center.y + mult;
	var z = center.z + mult;
	light1.position.z = z;
	light1.position.y = - y;
	light1.position.x = - x;
	light2.position.z = z;
	light2.position.x = - x;
	light2.position.y = y;
	light3.position.z = z;
	light3.position.x = x;
	light3.position.y = - y;
}

function addLight(){
	const sphereSize = 20;
	const group = new THREE.Group();
	scene.add( group );

	light1 = new THREE.PointLight( 0xddffdd, 1.0 );
	light1.position.z = 70;
	light1.position.y = - 70;
	light1.position.x = - 70;
	scene.add( light1 );
	
	light2 = new THREE.PointLight( 0xffdddd, 1.0 );
	light2.position.z = 70;
	light2.position.x = - 70;
	light2.position.y = 70;
	scene.add( light2 );
	
	light3 = new THREE.PointLight( 0xddddff, 1.0 );
	light3.position.z = 70;
	light3.position.x = 70;
	light3.position.y = - 70;
	scene.add( light3 );

	var lightAmbient = new THREE.AmbientLight(0xffffff, 0.6);
	scene.add(lightAmbient);
}

function showSnapPoint(){
	if (sphereHelper){
		raycaster.setFromCamera( pointer, camera );
		const intersections = raycaster.intersectObjects(OdooCad.items, true );
		var intersection = ( intersections.length ) > 0 ? intersections[ 0 ] : null;
		if (intersection !== null ) {
			var first = true;
			var nearestPoint = new THREE.Vector3( );
			var check_distance;
			var distance;
			var vertices = intersection.object.geometry.attributes.position.array;
			for (let i = 0; i < vertices.length; i=i+3) {
				var spoolVector = new THREE.Vector3( );
				spoolVector.x = vertices[i] + intersection.object.position.x;
				spoolVector.y = vertices[i+1] + intersection.object.position.y;
				spoolVector.z = vertices[i+2] + intersection.object.position.z;
				check_distance = intersection.point.distanceTo( spoolVector ) 
				if (first){
					distance = check_distance;
					nearestPoint = 	spoolVector;
					first = false;
				} else {
					if (check_distance < distance){
						distance = check_distance;
						nearestPoint = 	spoolVector;	
						/*
						 * console.log(distance); console.log("IP",
						 * intersection.point); console.log("SV", spoolVector);
						 * console.log("NP", nearestPoint);
						 */
					}
				}
		    }
			sphereHelper.position.copy(nearestPoint);
			sphereHelper.visible=true;
		} else{
			sphereHelper.visible=false;
		}
	}
	
}

function updateOrientationCube(camera){
    if(cube){
        const mat = new THREE.Matrix4();
        mat.extractRotation( camera.matrixWorldInverse );
        cube.style.transform = `translateZ(-100px) ${getCameraCSSMatrix( mat )}`;
        }
}

function render() {
    if(debug_3d){
        console.log("position");
        console.log(camera.position);
        console.log("rotation");
        console.log(camera.rotation);
    }
	resizeCanvasToDisplaySize();
	showSnapPoint();
	updateOrientationCube(camera);
	labelRenderer.render(scene, camera);
	renderer.render( scene, camera );
}

function tweenCamera(position){
    controls.target = new THREE.Vector3(0,0,0);
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
    fitCameraToSelection(OdooCad.items,
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
	  if(cube){
	   cube.style.left=clientWidth-100 + 'px';
	   cube.style.top=clientHeight-50 + 'px';
	  }
	}

function refreshIframe(){
/*
 * if (inIframe()){ refreshIframe();}
 */
	if (srcRefresh==false){
		var iframe = window.top.document.getElementById('embedded_odoo_plm_webgl');
		if (iframe){
			iframe.src = iframe.src;
		}
		srcRefresh=true;
	}
};

function getElementByXpath(path, document_env) {
	  return document_env.evaluate(path, document_env, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
}

document.addEventListener('DOMContentLoaded', function() {
	init();
	initcommand();
	render();
	}, false);

if (inIframe()){
		window.top[0].document.addEventListener('DOMContentLoaded', function(){
			var carousel = parent.document.getElementById('o-carousel-product');
			if (carousel ){
				var iframe =  parent.document.getElementById('embedded_odoo_plm_webgl');
				var title = document.querySelector("#odoo_plm_title");
				if (title){
					title.style.height='0.01px';
					title.style.border='1px solid white';
					title.children[0].remove;
				}
				var refreshed = iframe.getAttribute('o-plm-refreshed');
				if (refreshed=='false' || refreshed==null){
					carousel.addEventListener("click", function() {
						console.log("refreshed");
						refreshIframe();
					})	
					iframe.setAttribute('o-plm-refreshed', true);
			}	}
	},false);
	
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

export {camera}
export {tweenCamera}
