/*
 * treejs import
 */
import * as THREE from '../three.js/build/three.module.js';
/*
 * OdooCad import
 */
import * as ODOOLOADER from './loaders.js';

const html_canvas =  document.getElementById('odoo_canvas');

class OdooCAD{
	constructor(scene){
		this.scene = scene;
		this.loader = new ODOOLOADER.Loader(this);
		this.items = [];
	}
	/*
	 * load document from odoo using the built in loader
	 */
	load_document(document_id, document_name){
		this.loader.load_document(document_id, document_name);
	}
	
	addItemToScene(object){
		/*
		 * Add item to scene taking care of adding it to the geometry array
		 */
			object.receiveShadow=true;
			object.castShadow=true;
			this.scene.add(object);
			this.items.push(object);
			// Center the object
/*
			var bbox = new THREE.Box3().setFromObject(object);
			var center = new THREE.Vector3();
			bbox.getCenter(center);
			var xpos = center.x;
			xpos = xpos * -1;
			var ypos = bbox.min.y;
			ypos = ypos * -1;
			var zpos = center.z;
			zpos = zpos * -1;
			object.position.set(xpos,
								ypos,
								zpos);
*/
			progress.display = 'none';
			var fitItem = new CustomEvent("OdooCAD_fit_items");
			html_canvas.dispatchEvent(fitItem);
		}
		
		
		removeItemToSeen(object){
			/* TODO: make the remove operation */
		}
}

export {OdooCAD}