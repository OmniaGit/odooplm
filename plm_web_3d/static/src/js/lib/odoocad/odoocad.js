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

var guid = () => { var w = () => { return Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1); }
  return  `${w()}${w()}-${w()}-${w()}-${w()}-${w()}${w()}${w()}`;}
  
class OdooCAD{
	constructor(scene){
        this.tree_ref_elements={}
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
        var self=this;
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
            //
			this.scene.add(object);
			this.items.push(object);
			//
			const out_htm_structure = this.create_relation_structure(object);
			// Center the object
            // fit item
			progress.display = 'none';
			var fitItem = new CustomEvent("OdooCAD_fit_items");
			html_canvas.dispatchEvent(fitItem);
			// recompute the bounding box
			this.active_bbox=this.getBBox();
			return out_htm_structure;
		}
		//
		
		///
		set_str_name(span_element){
            var guid_name = span_element.parentElement.attributes['webgl_ref_name'].value;
            var obj_3d = this.tree_ref_elements[guid_name]
            var xmlhttp = new XMLHttpRequest();
            var url = "../plm/get_3d_web_document_info/?src_name=" + obj_3d.name;
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
                  if (object.children[i].type=='Group' || object.children[i].name!=''){
                     const [inner_html, children_found] = self.get_li_structure(object.children[i], true);
                     var obj_name = object.children[i].name;
                     var internal_obj_name = guid()
                     var span_lable = "<span class='document_tree_span' webgl_ref_name='" + internal_obj_name + "'>" + obj_name + "</span>";
                     if(children_found || object.children[i].name!=''){
                         self.tree_ref_elements[internal_obj_name] = object.children[i]
                         out_lis += "<li class='document_tree_line' webgl_ref_name="+ internal_obj_name +"><i class='tree_item_visibility fa fa-eye' aria-hidden='true'></i><span class='caret'>" + span_lable + "</span>" + inner_html + "</li>";
                     }
                     else{
                        out_lis += "<li class='document_tree_line' webgl_ref_name="+ internal_obj_name +">" + span_lable + "</li>";
                     }
                     found=true;
                  }
            }
            return  [out_lis + "</ul>", found];
        }
        //
        show_hide_item(guid_item_name, visible){
            var groupObj = self.tree_ref_elements[guid_item_name];
            if (groupObj){
                groupObj.visible=visible;
            }  else{
                console.log("Item " + item_name + " Not Found")
            }
        }
        //
        hide_all(){
            for( const scene_object_element of Object.values(this.tree_ref_elements) ) {
                scene_object_element.visible=false;
            }
        }
        //
        hide_item(guid_item_name){
            show_hide_item(guid_item_name, false);
        }
        //
        show_all(){
          for( const scene_object_element of Object.values(this.tree_ref_elements) ) {
              scene_object_element.visible=true;
          }
        }
        //
        show_item(guid_item_name){
            show_hide_item(guid_item_name, true);
        }
        //
        search_document_tree(element) { 
            var input, filter, ul, li, a, i, txtValue;
            input = document.getElementById("input_search_document_tree");
            filter = input.value.toUpperCase();
            ul = document.getElementById("document_tree");
            li = ul.getElementsByTagName("li");
            for (i = 0; i < li.length; i++) {
                a = li[i].getElementsByTagName("span")[0];
                txtValue = a.textContent || a.innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    li[i].style.display = "";
                } else {
                    li[i].style.display = "none";
                }
            }
        }
        //
        create_tree_structure(out_html_structure){
            const self = this;
            var html_out = "<div class='tree_structure' style='overflow-y: scroll;min-height: 1px;max-height: 400px;'>";
            html_out += out_html_structure
            html_out += "</div>";
            var li_document_tree = document.querySelectorAll('#document_tree')
            li_document_tree[0].innerHTML=html_out;
                        var toggler = document.getElementsByClassName("caret");
            var i;
            
            for (i = 0; i < toggler.length; i++) {
              toggler[i].onmouseover=function(){
                  var webgl_name = this.childNodes[0].attributes['webgl_ref_name'].value;
                  var groupObj = self.tree_ref_elements[webgl_name];
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
                  var webgl_name = this.childNodes[0].attributes['webgl_ref_name'].value;
                  var groupObj = self.tree_ref_elements[webgl_name];
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
                    var groupObj = self.tree_ref_elements[this.parentElement.attributes['webgl_ref_name'].value];
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
        //
		create_relation_structure(object){
            const grp_types = ["Group", "Object3D"];
            var self = this;
            
            var html_out = "";
            for (let i = 0; i < object.children.length; i++) {
                  if (grp_types.includes(object.children[i].type)){
                    const [inner_html, _children] = self.get_li_structure(object.children[i]);
                    html_out += inner_html;          
                  }
            }
            return html_out;
        }
		
		removeItemToSeen(object){
			/* TODO: make the remove operation */
		}
}

export {OdooCAD}