// treejs main import
import * as THREE from '../three.js/build/three.module.js';
// loaders
import { GLTFLoader } from '../three.js/examples/jsm/loaders/GLTFLoader.js';
import { FBXLoader } from '../three.js/examples/jsm/loaders/FBXLoader.js';
import { OBJLoader } from '../three.js/examples/jsm/loaders/OBJLoader.js';
import { VRMLLoader } from '../three.js/examples/jsm/loaders/VRMLLoader.js';
import { STLLoader } from '../three.js/examples/jsm/loaders/STLLoader.js';
import { SVGLoader } from '../three.js/examples/jsm/loaders/SVGLoader.js';
import { ThreeMFLoader } from '../three.js/examples/jsm/loaders/3MFLoader.js';
import { DXFLoader } from "./DXFLoader.js"


const gLTFLoader = new GLTFLoader();
const fBXLoader = new FBXLoader();
const oBJLoader = new OBJLoader();
const vRMLLoader = new VRMLLoader();
const stlLoader = new STLLoader();
const svgloader = new SVGLoader();
const dxfLoader = new DXFLoader();
const threeMFLoader = new ThreeMFLoader();
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
	constructor(odooCad) {
		this.odooCad = odooCad;
		this.overlay = document.querySelector('#loading_overlay');
	}

	_showProgress(document_name) {
		if (!this.overlay) return;
		this.overlay.style.display = 'flex';
		// Reset bar to 0 for each new load
		const bar = document.getElementById('loading_progress_bar');
		const pct = document.getElementById('loading_percent');
		if (bar) bar.style.width = '0%';
		if (pct) pct.textContent = '0%';
	}

	_updateProgress(xhr) {
		const bar = document.getElementById('loading_progress_bar');
		const pct = document.getElementById('loading_percent');
		if (!bar || !pct) return;
		if (xhr && xhr.lengthComputable && xhr.total > 0) {
			// Real percentage — Content-Length is set by download_treejs_model
			const percent = Math.min(100, Math.round((xhr.loaded / xhr.total) * 100));
			bar.style.width = percent + '%';
			pct.textContent = percent + '%';
		} else if (xhr && xhr.loaded > 0) {
			// Content-Length unknown — show bytes received as fallback
			const mb = (xhr.loaded / (1024 * 1024)).toFixed(1);
			pct.textContent = mb + ' MB received';
		}
	}

	_hideProgress() {
		if (!this.overlay) return;
		// Snap bar to 100% before hiding so the user sees completion
		const bar = document.getElementById('loading_progress_bar');
		const pct = document.getElementById('loading_percent');
		if (bar) bar.style.width = '100%';
		if (pct) pct.textContent = '100%';
		this.overlay.style.display = 'none';
		const canvas = document.getElementById('odoo_canvas');
		if (canvas) canvas.dispatchEvent(new Event('OdooCAD_fit_items'));
	}

	/*
	 * Load document from odoo
	 */
	load_document(document_id, document_name) {
		this._showProgress(document_name);
		var url = '../plm/download_treejs_model?document_id=' + document_id
		var exte = document_name.split('.').pop();
		exte = exte.toLowerCase()
		if (['glb', 'gltf'].includes(exte)) {
			this.loadGltx(document_name, url);
		}
		if (['fbx'].includes(exte)) {
			this.loadfBXLoader(document_name, url);
		}
		if (['obj'].includes(exte)) {
			this.loadoBJLoader(document_name, url);
		}
		if (['wrl'].includes(exte)) {
			this.loadvRMLLoader(document_name, url);
		}
		if (['json'].includes(exte)) {
			this.loadoloader(document_name, url);
		}
		if (['stl'].includes(exte)) {
			this.loadStlLoader(document_name, url);
		}
		if (['svg'].includes(exte)) {
			this.loadSvgLoader(document_name, url);
		}
		if (['dxf'].includes(exte)) {
			this.loadDxf(document_name, url);
		}
		if (['3mf'].includes(exte)) {
			this.load3mf(document_name, url);
		}
	}
	loadDxf(document_name, url) {
		var self = this;
		dxfLoader.load(url,
			function (objects, textEntities, origin) {
				for (const obj of objects) {
					self.odooCad.addItemToScene(obj);
				}
				if (textEntities && textEntities.length > 0) {
					self.odooCad.addDxfTextLabels(textEntities, origin);
				}
				self.odooCad.create_tree_structure("");
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}
	loadGltx(document_name, url) {
		var self = this;
		gLTFLoader.load(url,
			function (gltf) {
				var children = gltf.scene.children;
				var out_html_structure;
				for (var i = 0; i < children.length; i++) {
					out_html_structure += self.odooCad.addItemToScene(children[i]);
				}
				self.odooCad.create_tree_structure(out_html_structure);
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}

	load3mf(document_name, url) {
		var self = this;
		threeMFLoader.load(url,
			function (mfArgs) {
				mfArgs.traverse(function (child) { child.castShadow = true; });
				const out_html_structure = self.odooCad.addItemToScene(mfArgs, false);
				self.odooCad.create_tree_structure(out_html_structure);
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}

	loadfBXLoader(document_name, url) {
		var self = this;
		fBXLoader.load(url,
			function (gltf) {
				var out_html_structure = "";
				var children = gltf.children;
				for (var i = 0; i < children.length; i++) {
					out_html_structure += self.odooCad.addItemToScene(children[i]);
				}
				self.odooCad.create_tree_structure(out_html_structure);
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}

	loadoBJLoader(document_name, file_path) {
		var self = this;
		oBJLoader.load(file_path,
			function (objArgs) {
				var out_html_structure = "";
				var children = objArgs.children;
				for (var i = 0; i < children.length; i++) {
					out_html_structure += self.odooCad.addItemToScene(children[i]);
				}
				self.odooCad.create_tree_structure(out_html_structure);
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}


	loadoloader(document_name, url) {
		var self = this;
		loader.load(url,
			function (obj) {
				const out_html_structure = self.odooCad.addItemToScene(obj);
				self.odooCad.create_tree_structure(out_html_structure);
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}
	loadvRMLLoader(document_name, url) {
		var self = this;
		vRMLLoader.load(url,
			function (gltf) {
				var out_html_structure = "";
				var children = gltf.children;
				for (var i = 0; i < children.length; i++) {
					out_html_structure += self.odooCad.addItemToScene(children[i]);
				}
				self.odooCad.create_tree_structure(out_html_structure);
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}
	loadStlLoader(document_name, url) {
		var self = this;
		stlLoader.load(url,
			function (geometry) {
				const mesh = new THREE.Mesh(geometry, transparent_material);
				self.odooCad.addItemToScene(mesh);
				self.odooCad.create_tree_structure("");
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}


	loadSvgLoader(document_name, url) {
		var self = this;
		svgloader.load(url,
			function (data) {
				const paths = data.paths;
				const group = new THREE.Group();
				for (let i = 0; i < paths.length; i++) {
					const path = paths[i];
					const material = new THREE.MeshBasicMaterial({
						color: path.color,
						side: THREE.DoubleSide,
						depthWrite: false
					});
					const shapes = SVGLoader.createShapes(path);
					for (let j = 0; j < shapes.length; j++) {
						const shape = shapes[j];
						const geometry = new THREE.ShapeGeometry(shape);
						const mesh = new THREE.Mesh(geometry, material);
						group.add(mesh);
					}
				}
				self.odooCad.addItemToScene(group);
				self.odooCad.create_tree_structure("");
				self._hideProgress();
			},
			(xhr) => { self._updateProgress(xhr); },
			(err) => {
				self._hideProgress();
				alert("Unable to load the " + document_name + " err: " + err);
			}
		);
	}
}
export { Loader }
