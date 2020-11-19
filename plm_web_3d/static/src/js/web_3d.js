
import * as THREE from './lib/three.js/build/three.module.js';
import { GLTFLoader } from './lib/three.js/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from './lib/three.js/examples/jsm/controls/OrbitControls.js';
// to download an attachment from odoo use this template
//http://localhost:8069/web/content/ir.attachment/383/datas/aa.e

const loader = new GLTFLoader();
let camera, scene, renderer, controls;
const fov = 75;
const aspect = 2;  // the canvas default
const near = 0.1;
const far = 1000;
var fit_item = [];

function fitCameraToObject( camera, object, offset ) {

	offset = offset || 1.5;

	const boundingBox = new THREE.Box3();

	boundingBox.setFromObject( object );

	const center = boundingBox.getCenter( new THREE.Vector3() );
	const size = boundingBox.getSize( new THREE.Vector3() );

	const startDistance = center.distanceTo(camera.position);
	// here we must check if the screen is horizontal or vertical, because camera.fov is
	// based on the vertical direction.
	const endDistance = camera.aspect > 1 ?
						((size.y/2)+offset) / Math.abs(Math.tan(camera.fov/2)) :
						((size.y/2)+offset) / Math.abs(Math.tan(camera.fov/2)) / camera.aspect ;


	camera.position.set(
		camera.position.x * endDistance / startDistance,
		camera.position.y * endDistance / startDistance,
		camera.position.z * endDistance / startDistance,
		);
	camera.lookAt(center);
};

function fitCameraToSelection1( camera, controls, selection, fitOffset = 1.2 ) {
	  
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
	  
	  controls.update();
	  
};

function addAmbient(){
	  addCamera();
	  addLight();
	  addOrbit();
	  /*add gradient background*/

	  scene.background = new THREE.Color( 0xe0e0e0 );
	  scene.fog = new THREE.Fog( 0xe0e0e0, 20, 100 );;
	  // ground

	  const mesh = new THREE.Mesh( new THREE.PlaneBufferGeometry( 2000, 2000 ), new THREE.MeshPhongMaterial( { color: 0x999999, depthWrite: false } ) );
      mesh.rotation.x = - Math.PI / 2;
	  scene.add( mesh );

	  const grid = new THREE.GridHelper( 200, 40, 0x000000, 0x000000 );
      grid.material.opacity = 0.2;
	  grid.material.transparent = true;
	  scene.add( grid );
}


function init() {
  const canvas = document.querySelector('#odoo_canvas');
  renderer = new THREE.WebGLRenderer({canvas});
  scene = new THREE.Scene();
  addAmbient();
  loadDocumentFromOdoo()
}

function loadDocumentFromOdoo(){
	const document_id = document.querySelector('#active_model').getAttribute('active_model');
	var file_path =  '../web/content/ir.attachment/' + document_id + '/datas/download.glb';
	loader.load( file_path, function ( gltf ) {
		var children = gltf.scene.children; 
		var i;
		for (i = 0; i < children.length; i++) {
			addItemToSeen(children[i])
		}
		fitCameraToSelection1(camera, controls, fit_item, 1.1);
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
	/*TODO: make the remove operation */
}
function addCamera(){
	  camera = new THREE.PerspectiveCamera(fov, aspect, near, far);
	  camera.position.z = 2;
}

function addOrbit(){
	controls = new OrbitControls( camera, renderer.domElement );
	controls.addEventListener('change', render ); // use if there is no animation loop
	controls.minDistance = 2;
	controls.maxDistance = 10;
	controls.target.set( 0, 0, - 0.2 );
	controls.update();
}

function addLight(){
	
	const group = new THREE.Group();
	scene.add( group );

	const light = new THREE.PointLight( 0xddffdd, 1.0 );
	light.position.z = 70;
	light.position.y = - 70;
	light.position.x = - 70;
	scene.add( light );

	const light2 = new THREE.PointLight( 0xffdddd, 1.0 );
	light2.position.z = 70;
	light2.position.x = - 70;
	light2.position.y = 70;
	scene.add( light2 );

	const light3 = new THREE.PointLight( 0xddddff, 1.0 );
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
		fitCameraToSelection1(camera, controls, fit_item, 1.1);
		render();
	}
};

initcommand();
init();
render();
