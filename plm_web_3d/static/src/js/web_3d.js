
import * as THREE from './lib/three.js/build/three.module.js';
// loaders
import { GLTFLoader } from './lib/three.js/examples/jsm/loaders/GLTFLoader.js';
import { FBXLoader } from './lib/three.js/examples/jsm/loaders/FBXLoader.js';
import { OBJLoader } from './lib/three.js/examples/jsm/loaders/OBJLoader.js';
import { VRMLLoader } from './lib/three.js/examples/jsm/loaders/VRMLLoader.js';

// controls
import { OrbitControls } from './lib/three.js/examples/jsm/controls/OrbitControls.js';
// to download an attachment from odoo use this template
// http://localhost:8069/web/content/ir.attachment/383/datas/aa.e

const gLTFLoader = new GLTFLoader();
const fBXLoader = new FBXLoader();
const oBJLoader = new OBJLoader();
const vRMLLoader = new VRMLLoader();
const loader = new THREE.ObjectLoader();
let camera, scene, renderer, controls;
let planeMeshFloar, planeGrid;
let light1, light2, light3;
var srcRefresh = false;
var togleBackgoundV= false;
const fov = 75;
const aspect = 2;  // the canvas default
const near = 0.1;
const far = 1000;
var fit_item = [];


function fitCameraToSelection( camera, controls, selection, fitOffset = 1.2 ) {
	  
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

	  controls.maxDistance = distance * 10;
	  controls.target.copy( center );
	  
	  camera.near = distance / 100;
	  camera.far = distance * 100;
	  camera.updateProjectionMatrix();

	  camera.position.copy( controls.target ).sub(direction);
	  resetLight(size);
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
	  planeMeshFloar = new THREE.Mesh( new THREE.PlaneBufferGeometry( 2000, 2000 ), new THREE.MeshPhongMaterial( { color: 0x999999, depthWrite: false } ) );
	  planeGrid = new THREE.GridHelper( 200, 40, 0x000000, 0x000000 );
	  planeMeshFloar.rotation.x = - Math.PI / 2;
	  scene.add( planeMeshFloar );
	  planeGrid.material.opacity = 0.2;
	  planeGrid.material.transparent = true;
	  scene.add( planeGrid );
	  tecnicalBckground();
}

function togleBackgound(){
	if(togleBackgoundV){
		togleBackgoundV=false;
		tecnicalBckground();
	}
	else{
		togleBackgoundV=true;
		imageBckground();
	}
}


function tecnicalBckground(){
	planeGrid.visible=true;
	planeMeshFloar.visible=true;
	scene.background = new THREE.Color( 0xe0e0e0 );
	render();
}

function imageBckground(){
	const loader = new THREE.TextureLoader();
	planeGrid.visible=false;
	planeMeshFloar.visible=false;
	const texture = loader.load(
	  '/plm_web_3d/static/src/img/bakgroung_360/room.jpg',
	  () => {
	    const rt = new THREE.WebGLCubeRenderTarget(texture.image.height);
	    rt.fromEquirectangularTexture(renderer, texture);
	    scene.background = rt;
	    render();
	    controls.update();
	  });
}
function init() {
  const canvas = document.querySelector('#odoo_canvas');
  renderer = new THREE.WebGLRenderer({canvas});
  scene = new THREE.Scene();
  addAmbient();
  render();
  loadDocumentFromOdoo();
}



function loadDocumentFromOdoo(){
	const document_id = document.querySelector('#active_model').getAttribute('active_model');
	const document_name = document.querySelector('#active_model').getAttribute('document_name');
	var file_path =  '../web/content/ir.attachment/' + document_id + '/datas/' + document_name;
	var exte = document_name.split('.').pop();
	if (['glb'].includes(exte)){ 
		loadGltx(document_name, file_path);
	}
	if (['fbx'].includes(exte)){
		loadfBXLoader(document_name, file_path);
	}
	if (['obj'].includes(exte)){
		loadoBJLoader(document_name, file_path);
	}
	if (['loadvRMLLoader'].includes(exte)){
		loadoloader(document_name, file_path);
	}
	if (['json'].includes(exte)){
		loadoloader(document_name, file_path);
	}
	
}

function loadGltx(document_name, file_path){
	gLTFLoader.load( file_path, function ( gltf ) {
		var children = gltf.scene.children; 
		var i;
		for (i = 0; i < children.length; i++) {
			addItemToSeen(children[i])
		}
		fitCameraToSelection(camera, controls, fit_item, 1.1);
		render();
	}, undefined, function ( error ) {
		console.error( error.toString() );
	});	
	
}

function loadfBXLoader(document_name, file_path){
	fBXLoader.load( file_path, function ( gltf ) {
		var children = gltf.scene.children; 
		var i;
		for (i = 0; i < children.length; i++) {
			addItemToSeen(children[i])
		}
		fitCameraToSelection(camera, controls, fit_item, 1.1);
		render();
	}, undefined, function ( error ) {
		console.error( error.toString() );
	});	
	
}


function loadoBJLoader(document_name, file_path){
	oBJLoader.load( file_path, function ( gltf ) {
		var children = gltf.children; 
		var i;
		for (i = 0; i < children.length; i++) {
			addItemToSeen(children[i])
		}
		fitCameraToSelection(camera, controls, fit_item, 1.1);
		render();
	}, undefined, function ( error ) {
		console.error( error.toString() );
	});	
	
}

function loadoloader(document_name, file_path){
	loader.load(	// resource URL
			document_name,

			// onLoad callback
			// Here the loaded data is assumed to be an object
			function ( obj ) {
				// Add the loaded object to the scene
				addItemToSeen( obj );
			},

			// onProgress callback
			function ( xhr ) {
				console.log( (xhr.loaded / xhr.total * 100) + '% loaded' );
			},

			// onError callback
			function ( err ) {
				console.error( 'An error happened' );
			});	
}

function loadvRMLLoader(document_name, file_path){
	vRMLLoader.load( file_path, function ( gltf ) {
		var children = gltf.children; 
		var i;
		for (i = 0; i < children.length; i++) {
			addItemToSeen(children[i])
		}
		fitCameraToSelection(camera, controls, fit_item, 1.1);
		render();
	}, undefined, function ( error ) {
		console.error( error.toString() );
	});	
	
}
function addItemToSeen(object){
	scene.add(object);
	fit_item.push(object)	
}
function removeItemToSeen(objetc){
	/* TODO: make the remove operation */
}
function addCamera(){
	  camera = new THREE.PerspectiveCamera(fov, aspect, near, far);
	  camera.position.z = 2;
}

function addOrbit(){
	controls = new OrbitControls( camera, renderer.domElement );
	controls.addEventListener('change', render ); // use if there is no
													// animation loop
	controls.minDistance = 2;
	controls.maxDistance = 10;
	controls.target.set( 0, 0, - 0.2 );
	controls.update();
}

function resetLight(size) {
	var mult = 100;
	var x = size.x * mult;
	var y = size.x * mult;
	var z = size.x * mult;
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

function render() {
	renderer.render( scene, camera );
	resizeCanvasToDisplaySize();
}

function resizeCanvasToDisplaySize() {
	  const canvas = renderer.domElement;
	  // look up the size the canvas is being displayed
	  const width = canvas.clientWidth;
	  const height = canvas.clientHeight;

	  // adjust displayBuffer size to match
	  if (canvas.width !== width || canvas.height !== height) {
	    // you must pass false here or three.js sadly fights the browser
	    renderer.setSize(width, height, false);
	    camera.aspect = width / height;
	    camera.updateProjectionMatrix();

	    // update any render target sizes here
	  }
	}

function initcommand(){
	var element = document.getElementById("fit_view");
	element.onclick = function(event) {
		fitCameraToSelection(camera, controls, fit_item, 1.1);
		render();
	}
	var element = document.getElementById("togle_background");
	element.onclick = function(event) {
		togleBackgound();
	}
};


function inIframe () {
    try {
        return window.self !== window.top;
    } catch (e) {
        return true;
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


