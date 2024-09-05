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
		this.active_bbox=undefined;
		this.loader = new ODOOLOADER.Loader(this);
	}
	/*
	 * load document from odoo using the built in loader
	 */
	load_document(document_id, document_name){
		this.loader.load_document(document_id, document_name);
	}
    /*
     * Get the bounding box of all the added mesh items
     */
    getBBox(){
        
        const box = new THREE.Box3();
        var items = this.items;
        for (let i = 0; i < items.length; i=i+1) {
            items[i].traverse( function ( child ) {
                if ( child instanceof THREE.Mesh ) {
                    box.expandByObject(child)
                        }
                     });
                     };
        return box;
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
            // fit item
			progress.display = 'none';
			var fitItem = new CustomEvent("OdooCAD_fit_items");
			html_canvas.dispatchEvent(fitItem);
			// recompute the bounding box
			this.active_bbox=this.getBBox();
		}
		//
		
		///
		set_str_name(span_element){
            var file_name = span_element.parentElement.attributes['webgl_ref_name'].value;
            var xmlhttp = new XMLHttpRequest();
            var url = "../plm/get_3d_web_document_info/?src_name=" + file_name;
            xmlhttp.onreadystatechange = function() {
                if (this.readyState == 4 && this.status == 200) {
                    span_element.innerHTML = this.responseText;
                }
            };
            xmlhttp.open("GET", url, true);
            xmlhttp.send();
        }
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
                     var span_lable = "<span class='document_tree_span' webgl_ref_name='" + obj_name + "'>" + obj_name + "</span>";
                     if(children_found || object.children[i].name!=''){
                         tree_ref_elements[obj_name]=object.children[i]
                         out_lis += "<li class='document_tree_line' webgl_ref_name="+ obj_name +"><i class='tree_item_visibility fa fa-eye' aria-hidden='true'></i><span class='caret'>" + span_lable + "</span>" + inner_html + "</li>";
                     }
                     else{
                        out_lis += "<li class='document_tree_line' webgl_ref_name="+ obj_name +">" + span_lable + "</li>";
                     }
                     found=true;
                  }
            }
            return  [out_lis + "</ul>", found];
        }
        //
		create_relation_structure(object){
            var self = this;
            var html_out = "<div class='tree_structure' style='overflow-y: scroll;min-height: 1px;max-height: 400px;'>";
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
            //
            var tree_item_visibility = document.getElementsByClassName("tree_item_visibility");
            for (i = 0; i < tree_item_visibility.length; i++) {
                tree_item_visibility[i].addEventListener("click", function() {
                    var groupObj = tree_ref_elements[this.parentElement.attributes['webgl_ref_name'].value];
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
            //
            var span_tree_documents = document.getElementsByClassName("document_tree_span");
            for (i = 0; i < span_tree_documents.length; i++) {
                    this.set_str_name(tree_item_visibility[i])
                }
        }
		
		removeItemToSeen(object){
			/* TODO: make the remove operation */
		}
}

export {OdooCAD}