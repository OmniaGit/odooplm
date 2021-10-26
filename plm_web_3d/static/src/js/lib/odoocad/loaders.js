import * as THREE from '../three.js/build/three.module.js';
// loaders
import { GLTFLoader } from '../three.js/examples/jsm/loaders/GLTFLoader.js';
import { FBXLoader } from '../three.js/examples/jsm/loaders/FBXLoader.js';
import { OBJLoader } from '../three.js/examples/jsm/loaders/OBJLoader.js';
import { VRMLLoader } from '../three.js/examples/jsm/loaders/VRMLLoader.js';
import { STLLoader } from '../three.js/examples/jsm/loaders/STLLoader.js';

const gLTFLoader = new GLTFLoader();
const fBXLoader = new FBXLoader();
const oBJLoader = new OBJLoader();
const vRMLLoader = new VRMLLoader();
const stlLoader = new STLLoader();
const loader = new THREE.ObjectLoader();

const transparent_material = new THREE.MeshPhysicalMaterial({
    color: 0xb2ffc8,
    // envMap: envTexture,
    metalness: 0.25,
    roughness: 0.1,
    opacity: 1.0,
    transparent: true,
    transmission: 0.50,
    clearcoat: 1.0,
    clearcoatRoughness: 0.25
})

class Loader {
	constructor(odooCad){

		this.odooCad = odooCad;
		/*
		 * Progress Bar taken from document 
		 */
		this.progress = document.querySelector('#progress');
		this.progress_bar = document.querySelector('#progress_bar');
		this.progress.style.display = "none";
	}
	/*
	 * Load document from odoo
	 */
	load_document(document_id, document_name){
		this.progress_bar.style.width = '0%';
		this.progress.display = 'block';
		var file_path = '../plm/download_treejs_model?document_id=' + document_id
		var exte = document_name.split('.').pop();
		exte = exte.toLowerCase()
		if (['glb','gltf'].includes(exte)){ 
			this.loadGltx(document_name, file_path);
		}
		if (['fbx'].includes(exte)){
			this.loadfBXLoader(document_name, file_path);
		}
		if (['obj'].includes(exte)){
			this.loadoBJLoader(document_name, file_path);
		}
		if (['wrl'].includes(exte)){
			this.loadvRMLLoader(document_name, file_path);
		}
		if (['json'].includes(exte)){
			this.loadoloader(document_name, file_path);
		}
		if (['stl'].includes(exte)){
			this.loadStlLoader(document_name, file_path);
		}	
	}
	loadGltx(document_name, file_path){
		var self=this;
		gLTFLoader.load( file_path, function ( gltf ) {
			var children = gltf.scene.children; 
			var i;
			for (i = 0; i < children.length; i++) {
				self.addItemToScene(children[i]);
			}
		},
		function ( xhr ) {
	    	var percentage = (xhr.loaded / xhr.total) * 100;
	    	progress_bar.style.width = percentage + '%';
	        console.log(progress_bar.style.width + ' loaded')
		},

		function ( err ) {
			alert("Unable to load the " + document_name + " err: " + err);
		});		
	}
	loadfBXLoader(document_name, file_path){
		fBXLoader.load( file_path, function ( gltf ) {
			var children = gltf.children; 
			var i;
			for (i = 0; i < children.length; i++) {
				this.addItemToScene(children[i]);
			}
		},
		function ( xhr ) {
	    	var percentage = (xhr.loaded / xhr.total) * 100;
	    	this.progress_bar.style.width = percentage + '%';
	        console.log(progress_bar.style.width + ' loaded')
		},

		function ( err ) {
			alert("Unable to load the " + document_name + " err: " + err);
		});	
	}
	loadoBJLoader(document_name, file_path){
		oBJLoader.load( file_path, function ( gltf ) {
			var children = gltf.children; 
			var i;
			for (i = 0; i < children.length; i++) {
				this.addItemToScene(children[i]);
			}
		}, 
		function ( xhr ) {
	    	var percentage = (xhr.loaded / xhr.total) * 100;
	    	this.progress_bar.style.width = percentage + '%';
	        console.log(progress_bar.style.width + ' loaded')
		},
		function ( err ) {
			alert("Unable to load the " + document_name + " err: " + err);
		});	
		
	}
	loadoloader(document_name, file_path){
		loader.load(
				document_name,
				function ( obj ) {
					this.addItemToScene( obj );
				},

				function ( xhr ) {
			    	var percentage = (xhr.loaded / xhr.total) * 100;
			    	this.progress_bar.style.width = percentage + '%';
			        console.log(progress_bar.style.width + ' loaded')
				},

				function ( err ) {
					alert("Unable to load the " + document_name + " err: " + err);
				});	
	}
	loadvRMLLoader(document_name, file_path){
		vRMLLoader.load( file_path, function ( gltf ) {
			var children = gltf.children; 
			var i;
			for (i = 0; i < children.length; i++) {
				this.addItemToScene(children[i])
			}
		},
	    (xhr) => {
	    	var percentage = (xhr.loaded / xhr.total) * 100;
	    	this.progress_bar.style.width = percentage + '%';
	        console.log(progress_bar.style.width + ' loaded')
	    },
	    (err) => {
	    	alert("Unable to load the " + document_name + " err: " + err);
	    });	
	}
	loadStlLoader(document_name, file_path){
		var self=this;
		stlLoader.load(file_path, 
		    function (geometry) {
		        const mesh = new THREE.Mesh(geometry, transparent_material)
		        self.odooCad.addItemToScene(mesh);
		    },
		    (xhr) => {
		    	var percentage = (xhr.loaded / xhr.total) * 100;
		    	self.progress_bar.style.width = percentage + '%';
		        console.log(progress_bar.style.width + ' loaded')
		    },
		    (err) => {
		    	alert("Unable to load the " + document_name + " err: " + err);
		 });
	}
}
export {Loader}