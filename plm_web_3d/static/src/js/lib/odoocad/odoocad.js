/*
 * treejs import
 */
import * as THREE from '../three.js/build/three.module.js';
import { FontLoader } from '../three.js/examples/jsm/loaders/FontLoader.js';
import { TextGeometry } from '../three.js/examples/jsm/geometries/TextGeometry.js';
/*
 * OdooCad import
 */
import * as ODOOLOADER from './loaders.js';

const html_canvas = document.getElementById('odoo_canvas');
const odoo_hilight_color = new THREE.Color("#eda3da")

var guid = () => {
    var w = () => { return Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1); }
    return `${w()}${w()}-${w()}-${w()}-${w()}-${w()}${w()}${w()}${w()}`;
}

class OdooCAD {
    constructor(scene) {
        this.tree_ref_elements = {}
        this.scene = scene;
        this.items = [];
        this.active_bbox = undefined;
        this.loader = new ODOOLOADER.Loader(this);
    }
    /*
     * load document from odoo using the built in loader
     */
    load_document(document_id, document_name) {
        this.loader.load_document(document_id, document_name);
    }
    /*
     * Get the bounding box of all the added mesh items
     */
    getBBox() {

        const box = new THREE.Box3();
        var items = this.items;
        for (let i = 0; i < items.length; i = i + 1) {
            items[i].traverse(function (child) {
                if (child instanceof THREE.Mesh) {
                    box.expandByObject(child)
                }
            });
        };
        return box;
    }

    addItemToScene(object, force_material = true) {
        var self = this;
        /*
         * Add item to scene taking care of adding it to the geometry array
         */
        if (force_material === true) {
            object.receiveShadow = true;
            object.castShadow = true;
            var randomColor = "#000000".replace(/0/g, function () { return (~~(Math.random() * 16)).toString(16); });
            var material = new THREE.MeshPhongMaterial({ color: randomColor });
            object.traverse(function (child) {
                if (child instanceof THREE.Mesh) {
                    child.material = material;
                }
            });
            object.material = material;
        }
        //
        this.scene.add(object);
        this.items.push(object);
        //
        const out_htm_structure = this.create_relation_structure(object);
        // Center the object
        // fit item
        var fitItem = new CustomEvent("OdooCAD_fit_items");
        html_canvas.dispatchEvent(fitItem);
        // recompute the bounding box
        this.active_bbox = this.getBBox();
        return out_htm_structure;
    }

    set_str_name(span_element) {
        var guid_name = span_element.parentElement.attributes['webgl_ref_name'].value;
        var obj_3d = this.tree_ref_elements[guid_name]
        var xmlhttp = new XMLHttpRequest();
        var url = "../plm/get_3d_web_document_info/?src_name=" + obj_3d.name;
        xmlhttp.onreadystatechange = function () {
            if (this.readyState == 4 && this.status == 200) {
                span_element.innerHTML = this.responseText;
            }
        };
        xmlhttp.open("GET", url, true);
        xmlhttp.send();
    }

    // ============================================
    // MODIFIED FUNCTION #1: get_li_structure
    // ============================================
    get_li_structure(object, nested = false) {
        var self = this;
        var found = false;
        var out_lis = '';
        if (nested) {
            out_lis = '<ul class="nested">';
        }
        else {
            out_lis = '<ul id="myUL">';
        }

        // FIXED: Process all children, not just Groups
        for (let i = 0; i < object.children.length; i++) {
            const child = object.children[i];

            // Skip children with no name and no meaningful type
            if (child.name === '' && !['Group', 'Object3D', 'Mesh'].includes(child.type)) {
                continue;
            }

            // Recursively get children structure
            const [inner_html, children_found] = self.get_li_structure(child, true);
            var obj_name = child.name || child.type; // Use type as fallback name
            var clean_code = (child.name || "").split('(')[0].trim();
            var internal_obj_name = guid();
            var span_lable = "<span class='document_tree_span' webgl_ref_name='" + internal_obj_name + "'>" + obj_name + "</span>";

            // Get initial color
            var initialColor = "#b2ffc8"; // Default
            child.traverse(function (c) {
                if (c instanceof THREE.Mesh && c.material && c.material.color) {
                    initialColor = "#" + c.material.color.getHexString();
                }
            });
            var color_picker = "<input type='color' class='tree_item_color' webgl_ref_name='" + internal_obj_name + "' value='" + initialColor + "' title='Change Color'>";

            // Add item if it has children or a meaningful name
            if (children_found || child.name !== '') {
                self.tree_ref_elements[internal_obj_name] = child;
                child.userData.webgl_ref_name = internal_obj_name;
                child.userData.engineering_code = clean_code;

                // Check if the inner HTML actually contains any elements from sub-parts,
                // or if it's just an empty ul wrapper (because all children were 'body' nodes and got filtered).
                let has_visible_children = (inner_html !== '<ul class="nested"></ul>' && inner_html !== '<ul id="myUL"></ul>');

                // Only push to HTML if it's not a geometry body
                if (!(child.name || '').toLowerCase().startsWith('body')) {
                    if (has_visible_children) {
                        out_lis += "<li class='document_tree_line' webgl_ref_name='" + internal_obj_name + "'><i class='tree_item_visibility fa fa-eye' aria-hidden='true'></i>" + color_picker + "<span class='caret'>" + span_lable + "</span>" + inner_html + "</li>";
                    } else {
                        // Render as a leaf node without caret and without empty sub list
                        out_lis += "<li class='document_tree_line' webgl_ref_name='" + internal_obj_name + "'><i class='tree_item_visibility fa fa-eye' aria-hidden='true'></i>" + color_picker + " " + span_lable + "</li>";
                    }
                }
            }
            else if (child.name !== '') {
                // Leaf node with a name
                child.userData.webgl_ref_name = internal_obj_name;
                child.userData.engineering_code = clean_code;
                // Only push to HTML if it's not a geometry body
                if (!(child.name || '').toLowerCase().startsWith('body')) {
                    out_lis += "<li class='document_tree_line' webgl_ref_name='" + internal_obj_name + "'>" + color_picker + " " + span_lable + "</li>";
                }
            }

            found = found || children_found || (child.name !== '');
        }

        return [out_lis + "</ul>", found];
    }

    // ============================================
    // MODIFIED FUNCTION #2: show_hide_item
    // ============================================
    show_hide_item(guid_item_name, visible) {
        var groupObj = this.tree_ref_elements[guid_item_name];
        if (groupObj) {
            groupObj.visible = visible;
        } else {
            console.log("Item " + guid_item_name + " Not Found")  // FIXED: was item_name
        }
    }

    // ============================================
    // MODIFIED FUNCTION #3: hide_item
    // ============================================
    hide_item(guid_item_name) {
        this.show_hide_item(guid_item_name, false);  // FIXED: added 'this.'
    }

    // ============================================
    // MODIFIED FUNCTION #4: show_item
    // ============================================
    show_item(guid_item_name) {
        this.show_hide_item(guid_item_name, true);   // FIXED: added 'this.'
    }

    //
    hide_all() {
        for (const scene_object_element of Object.values(this.tree_ref_elements)) {
            scene_object_element.visible = false;
        }
    }

    //
    show_all() {
        for (const scene_object_element of Object.values(this.tree_ref_elements)) {
            scene_object_element.visible = true;
        }
    }

    //
    search_document_tree(element) {
        var input, filter, ul, li, a, i, txtValue;
        input = document.getElementById("input_search_document_list");
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

    create_tree_structure(out_html_structure) {
        const self = this;

        // Handle global color picker visibility (only if no structure)
        var globalColorPicker = document.getElementById("global_object_color");
        if (globalColorPicker) {
            // If structure is empty or just contains empty tags, show global picker
            if (!out_html_structure || out_html_structure.trim() === "" || out_html_structure === "<ul></ul>") {
                globalColorPicker.style.display = "inline-block";
                
                // Apply initial color if possible
                if (self.items.length > 0) {
                    self.items[0].traverse(function (c) {
                        if (c instanceof THREE.Mesh && c.material && c.material.color) {
                            globalColorPicker.value = "#" + c.material.color.getHexString();
                        }
                    });
                }

                // Add listener once (avoid duplicates if called multiple times)
                if (!globalColorPicker._listenerAdded) {
                    globalColorPicker.addEventListener("input", function (event) {
                        var selectedColor = this.value;
                        self.items.forEach(item => {
                            item.traverse(function (child) {
                                if (child instanceof THREE.Mesh && child.material) {
                                    child.material.color.setStyle(selectedColor);
                                    child.material.userData.originalColor = child.material.color.clone();
                                    child.material.userData.oldColor = child.material.color.clone();
                                }
                            });
                        });
                        
                        // Also update individual pickers in the tree if they exist
                        var itemPickers = document.getElementsByClassName("tree_item_color");
                        for (let picker of itemPickers) {
                            picker.value = selectedColor;
                        }

                        // Trigger render
                        var renderEvent = new CustomEvent("OdooCAD_render");
                        html_canvas.dispatchEvent(renderEvent);
                    });
                    globalColorPicker._listenerAdded = true;
                }
            } else {
                globalColorPicker.style.display = "none";
            }
        }

        var html_out = "<div class='tree_structure' style='overflow-y: scroll;min-height: 1px;max-height: 400px;'>";
        html_out += out_html_structure;
        html_out += "</div>";

        var li_document_tree = document.querySelectorAll('#document_tree');
        if (li_document_tree.length > 0) {
            li_document_tree[0].innerHTML = html_out;
        }

        // ✅ IMPORTANT: use full row instead of span
        var hoverTargets = document.getElementsByClassName("document_tree_line");

        for (let i = 0; i < hoverTargets.length; i++) {

            // =========================
            // HOVER IN
            // =========================
            hoverTargets[i].onmouseover = function (event) {
                event.stopPropagation();

                this.classList.add('hovered'); // ✅ full row highlight

                var webgl_name = this.getAttribute('webgl_ref_name');
                if (!webgl_name) return;

                var groupObj = self.tree_ref_elements[webgl_name];
                if (!groupObj) return;

                groupObj.traverse(function (child) {
                    if (child instanceof THREE.Mesh) {
                        if (child.material.userData.oldColor == undefined) {
                            child.material.userData.oldColor = child.material.color.clone();
                        }
                        child.material.color = odoo_hilight_color;
                    }
                });
            };

            // =========================
            // HOVER OUT
            // =========================
            hoverTargets[i].onmouseout = function (event) {
                event.stopPropagation();

                this.classList.remove('hovered');

                var webgl_name = this.getAttribute('webgl_ref_name');
                if (!webgl_name) return;

                var groupObj = self.tree_ref_elements[webgl_name];
                if (!groupObj) return;

                groupObj.traverse(function (child) {
                    if (child instanceof THREE.Mesh) {
                        if (child.material.userData.oldColor != undefined) {
                            child.material.color = child.material.userData.oldColor;
                        }
                    }
                });
            };

            // =========================
            // CLICK
            // =========================
            hoverTargets[i].addEventListener("click", function (event) {
                if (event.target.tagName != 'I' && event.target.tagName != 'INPUT') {
                    let url = location.origin;
                    let product_tag = document.getElementById('linked_component_id');

                    if (product_tag && product_tag.dataset.id) {
                        let product_id = product_tag.dataset.id;
                        url = url + '/odoo/product.product/' + product_id;
                        window.open(url);
                    }
                }
            });
        }

        // =========================
        // VISIBILITY TOGGLE
        // =========================
        var tree_item_visibility = document.getElementsByClassName("tree_item_visibility");

        for (let i = 0; i < tree_item_visibility.length; i++) {
            tree_item_visibility[i].addEventListener("click", function (event) {
                event.stopPropagation();

                function objectsVisibility(items, visible, currentAttrValue) {
                    items.forEach(name => {
                        var groupObj = self.tree_ref_elements[name];
                        if (!groupObj) return;

                        var groupDiv = document.querySelector(`.document_tree_line[webgl_ref_name="${name}"]`);

                        if (groupDiv && currentAttrValue !== name) {
                            var icon = groupDiv.querySelector('.tree_item_visibility');
                            if (icon) {
                                icon.classList.toggle('fa-eye', visible);
                                icon.classList.toggle('fa-eye-slash', !visible);
                            }
                        }

                        groupObj.visible = visible;
                    });
                }

                let currentAttrValue = this.parentElement.getAttribute('webgl_ref_name');
                let labelSpan = this.parentElement.querySelector('.document_tree_span');
                if (!labelSpan) return;

                let labelContent = labelSpan.textContent;

                const matchingSpans = Array.from(document.querySelectorAll('.document_tree_span'))
                    .filter(span => span.textContent === labelContent);

                let webglRefNames = matchingSpans
                    .map(span => span.getAttribute('webgl_ref_name'))
                    .filter(name => name !== null);

                let icon = this;
                let isVisible = icon.classList.contains('fa-eye');

                icon.classList.toggle('fa-eye', !isVisible);
                icon.classList.toggle('fa-eye-slash', isVisible);

                objectsVisibility(webglRefNames, !isVisible, currentAttrValue);
            });
        }

        // =========================
        // COLOR CHANGE
        // =========================
        var tree_item_color = document.getElementsByClassName("tree_item_color");
        for (let i = 0; i < tree_item_color.length; i++) {
            tree_item_color[i].addEventListener("input", function (event) {
                event.stopPropagation();
                var webgl_name = this.getAttribute('webgl_ref_name');
                var selectedColor = this.value;
                var groupObj = self.tree_ref_elements[webgl_name];
                if (groupObj) {
                    groupObj.traverse(function (child) {
                        if (child instanceof THREE.Mesh && child.material) {
                            child.material.color.setStyle(selectedColor);
                            child.material.userData.originalColor = child.material.color.clone();
                            child.material.userData.oldColor = child.material.color.clone();
                        }
                    });

                    // Trigger render
                    var renderEvent = new CustomEvent("OdooCAD_render");
                    html_canvas.dispatchEvent(renderEvent);
                }
            });
        }

        // =========================
        // CARET TOGGLE
        // =========================
        var carets = document.getElementsByClassName("caret");

        for (let i = 0; i < carets.length; i++) {
            carets[i].addEventListener("click", function (event) {

                if (event.target !== this) return;

                var nestedList = this.parentElement.querySelector(".nested");

                if (nestedList) {
                    nestedList.classList.toggle("active");
                    this.classList.toggle("caret-down");
                }

                event.stopPropagation();
            });
        }
    }


    // NOTE: set_str_name is disabled because it fetches from a backend API
    // which can return the login page HTML if the session is invalid,
    // corrupting the entire Document Structure tree with login page content.
    // var span_tree_documents = document.getElementsByClassName("document_tree_span");
    // for (i = 0; i < span_tree_documents.length; i++) {
    //     this.set_str_name(tree_item_visibility[i])
    // }

    //

    create_relation_structure(object) {
        const grp_types = ["Group", "Object3D"];
        var self = this;

        var html_out = "";
        for (let i = 0; i < object.children.length; i++) {
            if (grp_types.includes(object.children[i].type)) {
                const [inner_html, _children] = self.get_li_structure(object.children[i]);
                html_out += inner_html;
            }
        }
        return html_out;
    }

    removeItemToSeen(object) {
        /* TODO: make the remove operation */
    }

    addDxfTextLabels(textEntities, origin) {
        if (this._dxfTextGroup) {
            this.scene.remove(this._dxfTextGroup)
        }
        this._dxfTextGroup = new THREE.Group()
        this.scene.add(this._dxfTextGroup)

        const group = this._dxfTextGroup
        const material = new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.DoubleSide })
        const FONT_URL = '/plm_web_3d/static/src/js/lib/three.js/examples/fonts/helvetiker_regular.typeface.json'
        // DxfScene subtracts origin from every vertex; apply the same offset here.
        const ox = origin ? origin.x : 0
        const oy = origin ? origin.y : 0

        new FontLoader().load(FONT_URL, function (font) {
            for (const entry of textEntities) {
                const size = entry.textHeight > 0 ? entry.textHeight : 2.5
                const rotZ = (entry.rotation || 0) * Math.PI / 180
                const lines = entry.text.split('\n')
                const lineHeight = size * 1.4

                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim()
                    if (!line) continue

                    const geometry = new TextGeometry(line, {
                        font: font,
                        size: size,
                        height: 0,
                        curveSegments: 4,
                        bevelEnabled: false,
                    })

                    const mesh = new THREE.Mesh(geometry, material)
                    const dx = -Math.sin(rotZ) * i * lineHeight
                    const dy = -Math.cos(rotZ) * i * lineHeight
                    mesh.position.set(entry.x - ox + dx, entry.y - oy - dy, 0)
                    mesh.rotation.z = rotZ
                    group.add(mesh)
                }
            }
        })
    }
}

export { OdooCAD }
