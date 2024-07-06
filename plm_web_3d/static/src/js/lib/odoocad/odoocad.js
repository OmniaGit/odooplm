/*
 * treejs import
 */
import * as THREE from '../three.js/build/three.module.js';
/*
 * OdooCad import
 */
import * as ODOOLOADER from './loaders.js';

const html_canvas = document.getElementById('odoo_canvas');
const odoo_hilight_color= new THREE.Color("#eda3da")
var tree_ref_elements={};

class OdooCAD{
	constructor(scene){
		this.scene = scene;
		this.items = [];
		this.loader = new ODOOLOADER.Loader(this);
	}
	/*
	 * load document from odoo using the built in loader
	 */
	load_document(document_id, document_name){
		this.loader.load_document(document_id, document_name);
	}
    
	addItemToScene(object, force_material=true){
		/*
		 * Add item to scene taking care of adding it to the geometry array
		 */
            if (force_material===true){
    			object.receiveShadow=true;
    			object.castShadow=true;
    			var randomColor = "#000000".replace(/0/g,function(){return (~~(Math.random()*16)).toString(16);});
    			var material = new THREE.MeshPhongMaterial( { color:randomColor } );
                object.traverse( function ( child ) {
                    if ( child instanceof THREE.Mesh ) {
                        child.material = material;
                        }
                     });
                object.material=material;
            }
			this.scene.add(object);
			this.items.push(object);
			this.create_relation_structure(object);
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
            // populate tree view
            
            // fit item
			progress.display = 'none';
			var fitItem = new CustomEvent("OdooCAD_fit_items");
			html_canvas.dispatchEvent(fitItem);
		}
		//
		
		///
		get_li_structure(object, nested=false){
            var self = this;
            var found=false;
            var out_lis='';
            if (nested){
                out_lis='<ul class="nested">';
            }
            else{
                out_lis='<ul id="myUL">';
            }
            
            for (let i = 0; i < object.children.length; i++) {
                  if (object.children[i].type=='Group' ||object.children[i].name!=''){
                     const [inner_html, children_found] = self.get_li_structure(object.children[i], true);
                     var obj_name=object.children[i].name;
                     if(children_found || object.children[i].name!=''){
                         tree_ref_elements[obj_name]=object.children[i]
                         out_lis += "<li class='document_tree_line'><i class='tree_item_visibility fa fa-eye' aria-hidden='true'></i><span class='caret'>" + obj_name + "</span>"+inner_html+"</li>";
                     }
                     else{
                        out_lis += "<li class='document_tree_line'>" + obj_name + "</li>";
                     }
                     found=true;         
                  }
            }
            return  [out_lis + "</ul>", found];
        }
        //
		create_relation_structure(object){
            var self = this;
            var html_out = "<div class='tree_structure'>";
            for (let i = 0; i < object.children.length; i++) {
                  if (object.children[i].type=='Group'){
                    const [inner_html, _children] = self.get_li_structure(object.children[i]);
                    html_out += inner_html;          
                  }
            }
            html_out += "</div>";
            
            var li_document_tree = document.querySelectorAll('#document_tree')
            li_document_tree[0].innerHTML=html_out;
            var toggler = document.getElementsByClassName("caret");
            var i;
            
            for (i = 0; i < toggler.length; i++) {
              toggler[i].onmouseover=function(){
                  var groupObj = tree_ref_elements[this.innerText];
                  groupObj.traverse( function ( child ) {
                      if ( child instanceof THREE.Mesh ) {
                          if(child.material.userData.oldColor==undefined){
                              child.material.userData.oldColor=child.material.color;
                          }
                          child.material.color=odoo_hilight_color;
                      }
                  });
              }
              toggler[i].onmouseout=function(){
                  var groupObj = tree_ref_elements[this.innerText];
                  groupObj.traverse( function ( child ) {
                      if ( child instanceof THREE.Mesh ) {
                         if(child.material.userData.oldColor!=undefined){
                            child.material.color=child.material.userData.oldColor;
                         }
                      }
                  });
              }
              toggler[i].addEventListener("click", function() {
                this.parentElement.querySelector(".nested").classList.toggle("active");
                this.classList.toggle("caret-down");
              });
            }
            
            var tree_item_visibility = document.getElementsByClassName("tree_item_visibility");
            for (i = 0; i < tree_item_visibility.length; i++) {
                tree_item_visibility[i].addEventListener("click", function() {
                    var groupObj = tree_ref_elements[this.nextElementSibling.innerText];
                    var icon = this;
                      if (icon.classList.contains('fa-eye')) {
                        icon.classList.remove('fa-eye');
                        icon.classList.add('fa-eye-slash');
                        groupObj.visible=false;
                      } 
                      else {
                        icon.classList.remove('fa-eye-slash');
                        icon.classList.add('fa-eye');
                        groupObj.visible=true;
                      }
                    });
                }
        }
		
		removeItemToSeen(object){
			/* TODO: make the remove operation */
		}
}

export {OdooCAD}