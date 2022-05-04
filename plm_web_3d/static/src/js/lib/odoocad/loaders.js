// treejs main import
import * as THREE from '../three.js/build/three.module.js';
// loaders
import { GLTFLoader } from '../three.js/examples/jsm/loaders/GLTFLoader.js';
import { FBXLoader } from '../three.js/examples/jsm/loaders/FBXLoader.js';
import { OBJLoader } from '../three.js/examples/jsm/loaders/OBJLoader.js';
import { VRMLLoader } from '../three.js/examples/jsm/loaders/VRMLLoader.js';
import { STLLoader } from '../three.js/examples/jsm/loaders/STLLoader.js';
import { SVGLoader } from '../three.js/examples/jsm/loaders/SVGLoader.js';
import { DXFLoader } from "./DXFLoader.js"


const gLTFLoader = new GLTFLoader();
const fBXLoader = new FBXLoader();
const oBJLoader = new OBJLoader();
const vRMLLoader = new VRMLLoader();
const stlLoader = new STLLoader();
const svgloader = new SVGLoader();
const dxfLoader = new DXFLoader();
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
		var url = '../plm/download_treejs_model?document_id=' + document_id
		var exte = document_name.split('.').pop();
		exte = exte.toLowerCase()
		if (['glb','gltf'].includes(exte)){ 
			this.loadGltx(document_name, url);
		}
		if (['fbx'].includes(exte)){
			this.loadfBXLoader(document_name, url);
		}
		if (['obj'].includes(exte)){
			this.loadoBJLoader(document_name, url);
		}
		if (['wrl'].includes(exte)){
			this.loadvRMLLoader(document_name, url);
		}
		if (['json'].includes(exte)){
			this.loadoloader(document_name, url);
		}
		if (['stl'].includes(exte)){
			this.loadStlLoader(document_name, url);
		}	
        if (['svg'].includes(exte)){
            this.loadSvgLoader(document_name, url);
        }   
        if (['dxf'].includes(exte)){
            this.loadDxf(document_name, url);
        }   
	}
	loadDxf(document_name, url){
        var self=this;
        dxfLoader.load(url,
            function (objects) {
                for (const obj of objects) {
                   self.odooCad.addItemToScene(obj)
                }
            },
            (xhr) => {
                var percentage = (xhr.loaded / xhr.total) * 100;
                self.progress_bar.style.width = percentage + '%';
                console.log(self.progress_bar.style.width + ' loaded')
            },
            (err) => {
                alert("Unable to load the " + document_name + " err: " + err);
         });
	}
	loadGltx(document_name, url){
		var self=this;
		gLTFLoader.load( url, function ( gltf ) {
			var children = gltf.scene.children; 
			var i;
			for (i = 0; i < children.length; i++) {
				self.odooCad.addItemToScene(children[i]);
			}
		},
		function ( xhr ) {
	    	var percentage = (xhr.loaded / xhr.total) * 100;
	    	self.progress_bar.style.width = percentage + '%';
	        console.log(self.progress_bar.style.width + ' loaded')
		},

		function ( err ) {
			alert("Unable to load the " + document_name + " err: " + err);
		});		
	}
	loadfBXLoader(document_name, url){
	   var self=this;
		fBXLoader.load( url, function ( gltf ) {
			var children = gltf.children; 
			var i;
			for (i = 0; i < children.length; i++) {
				self.odooCad.addItemToScene(children[i]);
			}
		},
		function ( xhr ) {
	    	var percentage = (xhr.loaded / xhr.total) * 100;
	    	self.progress_bar.style.width = percentage + '%';
	        console.log(self.progress_bar.style.width + ' loaded')
		},

		function ( err ) {
			alert("Unable to load the " + document_name + " err: " + err);
		});	
	}
	
	loadoBJLoader(document_name, file_path){
	   var self=this;
		oBJLoader.load( file_path, function ( gltf ) {
			var children = gltf.children; 
			var i;
			for (i = 0; i < children.length; i++) {
				self.odooCad.addItemToScene(children[i]);
			}
		}, 
		function ( xhr ) {
	    	var percentage = (xhr.loaded / xhr.total) * 100;
	    	self.progress_bar.style.width = percentage + '%';
	        console.log(self.progress_bar.style.width + ' loaded')
		},
		function ( err ) {
			alert("Unable to load the " + document_name + " err: " + err);
		});	
		
	}
	loadoloader(document_name, url){
	   var self=this;
		loader.load(
				url,
				function ( obj ) {
					self.odooCad.addItemToScene( obj );
				},

				function ( xhr ) {
			    	var percentage = (xhr.loaded / xhr.total) * 100;
			         self.progress_bar.style.width = percentage + '%';
			        console.log(self.progress_bar.style.width + ' loaded')
				},

				function ( err ) {
					alert("Unable to load the " + document_name + " err: " + err);
				});	
	}
	loadvRMLLoader(document_name, url){
	   var self=this;
		vRMLLoader.load( url, function ( gltf ) {
			var children = gltf.children; 
			var i;
			for (i = 0; i < children.length; i++) {
				self.odooCad.addItemToScene(children[i])
			}
		},
	    (xhr) => {
	    	var percentage = (xhr.loaded / xhr.total) * 100;
	    	self.progress_bar.style.width = percentage + '%';
	        console.log(self.progress_bar.style.width + ' loaded')
	    },
	    (err) => {
	    	alert("Unable to load the " + document_name + " err: " + err);
	    });	
	}
	loadStlLoader(document_name, url){
		var self=this;
		stlLoader.load(url, 
		    function (geometry) {
		        const mesh = new THREE.Mesh(geometry, transparent_material)
		        self.odooCad.addItemToScene(mesh);
		    },
		    (xhr) => {
		    	var percentage = (xhr.loaded / xhr.total) * 100;
		    	self.progress_bar.style.width = percentage + '%';
		        console.log(self.progress_bar.style.width + ' loaded')
		    },
		    (err) => {
		    	alert("Unable to load the " + document_name + " err: " + err);
		 });
	}
    loadSvgLoader(document_name, url){
        var self=this;
        stlLoader.load(url, 
            function (data) {
                const paths = data.paths;
                const group = new THREE.Group();

                for ( let i = 0; i < paths.length; i ++ ) {
                    const path = paths[ i ];
                    const material = new THREE.MeshBasicMaterial( {
                        color: path.color,
                        side: THREE.DoubleSide,
                        depthWrite: false
                    });
                    const shapes = SVGLoader.createShapes( path );
                    for ( let j = 0; j < shapes.length; j ++ ) {
                        const shape = shapes[ j ];
                        const geometry = new THREE.ShapeGeometry( shape );
                        const mesh = new THREE.Mesh( geometry, material );
                        group.add( mesh );                   
                    }
                }
                scene.add( group );
            },
            (xhr) => {
                var percentage = (xhr.loaded / xhr.total) * 100;
                self.progress_bar.style.width = percentage + '%';
                console.log(self.progress_bar.style.width + ' loaded')
            },
            (err) => {
              
                 alert("Unable to load the " + document_name + " err: " + err);
            }
            );
    }
}
export {Loader}