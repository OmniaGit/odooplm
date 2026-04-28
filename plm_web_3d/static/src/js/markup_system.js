/** @odoo-module **/

let _editingMarkupId = null;
let fabricCanvas = null;
let currentTool = null;
let startX, startY;
let tempShape = null;
let undoStack = [];
let redoStack = [];
let isRedoing = false;
let _isLoadingJSON = false;
let _baseScreenshotData = null;
let _currentBaseImage = null;
let isSnapshotEditMode = false;
let _currentSnapshotUrl = null;
let _snapshotScale = 1;
let _markupsInitialised = false;
let _loadGeneration = 0;
let _hasChanges = false;

window.addEventListener("load", () => {
    const markupBtn = document.getElementById("markup_button");
    const markupBtnPerm = document.getElementById("markup_button_perm");
    if (markupBtn) markupBtn.addEventListener("click", openMarkupEditor);
    if (markupBtnPerm) markupBtnPerm.addEventListener("click", openMarkupEditor);

});

window.addEventListener("load", function() {
    const submitBtn = document.getElementById("submit_markup");
    if (submitBtn) submitBtn.addEventListener("click", submitMarkup);
    initExistingMarkups();
});

function _positionEditorControls(tRect) {
    const editor = document.getElementById("markup_editor");
    if (!editor) return;

    var toolbar = document.getElementById("markup_toolbar");
    var commentBox = document.getElementById("markup_comment_box");
    if (toolbar) toolbar.style.display = "none";
    if (commentBox) commentBox.style.display = "none";

    var existing = document.getElementById("markup_controls_row");
    if (existing) existing.parentNode.removeChild(existing);

    var wrap = document.createElement("div");
    wrap.id = "markup_controls_row";
    wrap.className = "mcr-wrap";

    if (toolbar) {
        var tbClone = toolbar.cloneNode(true);
        tbClone.id = "markup_toolbar_inner";
        tbClone.className = "mcr-toolbar";
        tbClone.removeAttribute("style");

        var origBtns = toolbar.querySelectorAll("button");
        var cloneBtns = tbClone.querySelectorAll("button");
        cloneBtns.forEach(function(btn, i) {
            btn.removeAttribute("style");
            btn.className = "mcr-btn";
            btn.onclick = function(e) {
                e.stopPropagation();
                if (origBtns[i]) origBtns[i].click();
            };
        });
        wrap.appendChild(tbClone);
    }

    var commentRow = document.createElement("div");
    commentRow.className = "mcr-comment-row";

    var commentInput = document.createElement("input");
    commentInput.id = "markup_comment_inner";
    commentInput.type = "text";
    commentInput.placeholder = "Write Message...";
    commentInput.className = "mcr-input";

    commentInput.addEventListener("input", function() {
        _hasChanges = true;
    });

    var activityPanelClone = document.createElement("div");
    activityPanelClone.id = "mcr_activity_panel";
    activityPanelClone.className = "mcr-activity-panel";
    activityPanelClone.style.display = "none";

    var today = new Date().toISOString().split("T")[0];
    activityPanelClone.innerHTML =
        "<div class=\"mcr-ap-row\">" +
        "<label class=\"mcr-ap-label\">Due Date</label>" +
        "<input type=\"date\" id=\"mcr_due_date\" class=\"mcr-ap-input\" value=\"" + today + "\"/>" +
        "</div>" +
        "<div class=\"mcr-ap-row\">" +
        "<label class=\"mcr-ap-label\">Summary</label>" +
        "<input type=\"text\" id=\"mcr_summary\" class=\"mcr-ap-input\" placeholder=\"Summary\"/>" +
        "</div>" +
        "<div class=\"mcr-ap-row\">" +
        "<label class=\"mcr-ap-label\">Assigned To</label>" +
        "<select id=\"mcr_user_id\" class=\"mcr-ap-input\"><option value=\"\">Loading users...</option></select>" +
        "</div>";

    fetch("/web/dataset/call_kw", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            jsonrpc: "2.0", method: "call",
            params: {
                model: "res.users", method: "search_read",
                args: [[["share", "=", false], ["active", "=", true]]],
                kwargs: {fields: ["id", "name"], order: "name asc", limit: 100},
            },
        }),
    })
        .then(function(r) {
            return r.json();
        })
        .then(function(data) {
            var sel = document.getElementById("mcr_user_id");
            if (!sel) return;
            var users = data.result || [];
            sel.innerHTML = "";
            users.forEach(function(u) {
                var opt = document.createElement("option");
                opt.value = u.id;
                opt.textContent = u.name;
                sel.appendChild(opt);
            });
            if (window.odoo && odoo.session_info && odoo.session_info.uid) {
                sel.value = odoo.session_info.uid;
            }
        })
        .catch(function() {
            var sel = document.getElementById("mcr_user_id");
            if (sel) sel.innerHTML = "<option value=\"\">Error loading users</option>";
        });

    var activityLabel = document.createElement("label");
    activityLabel.className = "mcr-activity-label";
    activityLabel.title = "Schedule Activity";

    var activityCheck = document.createElement("input");
    activityCheck.type = "checkbox";
    activityCheck.className = "mcr-activity-check";
    activityCheck.onchange = function() {
        var orig = document.getElementById("activity_view");
        if (orig) {
            orig.checked = this.checked;
            orig.dispatchEvent(new Event("change"));
        }
        if (activityPanelClone) {
            activityPanelClone.style.display = this.checked ? "block" : "none";
        }
    };
    activityLabel.appendChild(activityCheck);

    var submitBtn = document.createElement("button");
    submitBtn.textContent = "Submit";
    submitBtn.className = "mcr-submit";
    submitBtn.onclick = function(e) {
        e.stopPropagation();
        var orig = document.getElementById("markup_comment");
        if (orig) orig.value = commentInput.value;
        submitMarkup();
    };

    commentRow.appendChild(commentInput);
    commentRow.appendChild(activityLabel);
    commentRow.appendChild(submitBtn);

    var commentGroup = document.createElement("div");
    commentGroup.className = "mcr-comment-group";
    if (activityPanelClone) commentGroup.appendChild(activityPanelClone);
    commentGroup.appendChild(commentRow);

    wrap.appendChild(commentGroup);
    if (_editingMarkupId) {
        commentGroup.style.display = "none";

        var saveBtn = document.createElement("button");
        saveBtn.id = "mcr_save_existing_btn";
        saveBtn.className = "mcr-btn";
        saveBtn.textContent = "💾 Save";
        saveBtn.onclick = function(e) {
            e.stopPropagation();

            const threeCanvas = document.getElementById("odoo_canvas");

            // ✅ Merge canvas
            const mergedCanvas = document.createElement("canvas");
            mergedCanvas.width = threeCanvas.width;
            mergedCanvas.height = threeCanvas.height;

            const ctx = mergedCanvas.getContext("2d");
            ctx.drawImage(threeCanvas, 0, 0);
            ctx.drawImage(fabricCanvas.lowerCanvasEl, 0, 0);

            const finalImage = mergedCanvas.toDataURL("image/png");

            // ✅ Clean JSON
            const fabricJsonObj = fabricCanvas.toJSON();
            if (fabricJsonObj.backgroundImage) delete fabricJsonObj.backgroundImage;
            const canvasJsonStr = JSON.stringify(fabricJsonObj);

            fetch("/plm/markup/update", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    jsonrpc: "2.0", method: "call",
                    params: {
                        markup_id: _editingMarkupId,
                        image: finalImage,
                        base_image: _currentBaseImage,
                        comment: displayComment,
                        filename: "markup_edit.jpg",
                        canvas_json: canvasJsonStr,

                        // REQUIRED
                        res_model: container.dataset.resModel,
                        res_id: parseInt(container.dataset.resId),

                        schedule_activity: false,
                    },
                }),
            })
                .then(r => r.json())
                .then(data => {
                    if (data.result?.success) {
                        showToast("Markup saved successfully!", "success");

                        // ← Update log item in UI without page reload
                        const logItem = document.querySelector(`[data-markup-id="${_editingMarkupId}"]`);
                        if (logItem) {
                            // Update snapshot shown in eye/modal
                            const eye = logItem.querySelector(".markup_log_eye");
                            const edit = logItem.querySelector(".markup_log_load");

                            if (eye && edit) {
                                const newEye = eye.cloneNode(true);
                                const newEdit = edit.cloneNode(true);

                                // Capture current values for closure
                                const savedImage = finalImage;
                                const savedCanvasJson = canvasJsonStr;
                                const savedBaseImage = _currentBaseImage;
                                const savedMarkupId = _editingMarkupId;
                                const savedComment = logItem.dataset.comment;
                                const savedDate = logItem.dataset.date;

                                newEye.addEventListener("click", function(e) {
                                    e.stopPropagation();
                                    openMarkupLogModal(savedImage, savedComment, savedDate);
                                });

                                newEdit.addEventListener("click", function(e) {
                                    e.stopPropagation();
                                    loadMarkupIntoEditor(savedCanvasJson, savedBaseImage, savedMarkupId);
                                });

                                eye.replaceWith(newEye);
                                edit.replaceWith(newEdit);

                                // Update row click too
                                logItem.onclick = function() {
                                    openMarkupLogModal(savedImage, savedComment, savedDate);
                                };
                            }
                        }

                        _hasChanges = false;
                        _closeEditor();
                    } else {
                        showToast("Failed to save markup.", "danger");
                    }
                })
                .catch(err => {
                    console.error("Save existing markup error:", err);
                    showToast("Something went wrong while saving.", "danger");
                });
        };

        tbClone.appendChild(saveBtn);
    }

    editor.appendChild(wrap);
}

function _resetEditorControls() {
    var row = document.getElementById("markup_controls_row");
    if (row && row.parentNode) row.parentNode.removeChild(row);
    var toolbar = document.getElementById("markup_toolbar");
    var commentBox = document.getElementById("markup_comment_box");
    if (toolbar) toolbar.style.display = "none";
    if (commentBox) commentBox.style.display = "none";
}

function _setSidePanelsAbove(above) {
    var container = document.getElementById("main_3d_web");
    if (!container) return;
    Array.from(container.children).forEach(function(child) {
        if (child.id !== "markup_editor" && child.id !== "odoo_canvas") {
            child.style.zIndex = above ? "200" : "";
        }
    });
}

function openMarkupEditor() {
    const editor = document.getElementById("markup_editor");
    const threeCanvas = document.getElementById("odoo_canvas");
    const container = document.getElementById("main_3d_web");
    if (!editor || !threeCanvas || !container) return;

    container.style.position = "relative";

    const tRect = threeCanvas.getBoundingClientRect();
    const cRect = container.getBoundingClientRect();

    const left = tRect.left - cRect.left;
    const top = tRect.top - cRect.top;
    const w = tRect.width;
    const h = tRect.height;

    editor.style.cssText = [
        "display: block",
        "position: absolute",
        "left: " + left + "px",
        "top: " + top + "px",
        "width: " + w + "px",
        "height: " + h + "px",
        "margin: 0",
        "padding: 0",
        "overflow: hidden",
        "z-index: 100",
        "pointer-events: auto",
        "box-sizing: border-box",
    ].join(";");

    _positionEditorControls(tRect);
    _setSidePanelsAbove(true);

    const rawCanvas = document.getElementById("markup_canvas");
    if (rawCanvas) {
        rawCanvas.width = w;
        rawCanvas.height = h;
    }

    if (!fabricCanvas) {
        fabricCanvas = new fabric.Canvas("markup_canvas");
        fabricCanvas.setWidth(w);
        fabricCanvas.setHeight(h);
        initFabricEvents();
        initToolbar();
    } else {
        fabricCanvas.setWidth(w);
        fabricCanvas.setHeight(h);
    }

    if (!isSnapshotEditMode) {
        try {
            _baseScreenshotData = threeCanvas.toDataURL("image/png");
        } catch (e) {
            console.warn("Screenshot capture failed:", e);
            _baseScreenshotData = null;
        }
    }

    _hasChanges = false;
}

function saveState() {
    if (isRedoing) return;
    if (_isLoadingJSON) return;
    undoStack.push(JSON.stringify(fabricCanvas));
    redoStack = [];
}

function undo() {
    if (undoStack.length === 0) return;

    isRedoing = true;
    redoStack.push(JSON.stringify(fabricCanvas));

    _isLoadingJSON = true;
    fabricCanvas.loadFromJSON(undoStack.pop(), function() {

        _isLoadingJSON = false;
        if (_currentBaseImage) {
            _reapplyBaseBackground(() => {
                isRedoing = false;
                _hasChanges = true;
            });
        } else if (isSnapshotEditMode && _currentSnapshotUrl) {
            _reapplySnapshotBackground(() => {
                isRedoing = false;
                _hasChanges = true;
            });
        } else {
            fabricCanvas.renderAll();
            isRedoing = false;
            _hasChanges = true;
        }
    });
}

function redo() {
    if (redoStack.length === 0) return;

    isRedoing = true;
    undoStack.push(JSON.stringify(fabricCanvas));

    _isLoadingJSON = true;

    fabricCanvas.loadFromJSON(redoStack.pop(), function() {

        _isLoadingJSON = false;

        if (_currentBaseImage) {
            _reapplyBaseBackground(() => {
                isRedoing = false;
                _hasChanges = true;
            });
        } else if (isSnapshotEditMode && _currentSnapshotUrl) {
            _reapplySnapshotBackground(() => {
                isRedoing = false;
                _hasChanges = true;
            });
        } else {
            fabricCanvas.renderAll();
            isRedoing = false;
            _hasChanges = true;
        }
    });
}

function initToolbar() {
    const actions = {
        "draw_btn": () => {
            currentTool = "draw";
            fabricCanvas.isDrawingMode = true;
            fabricCanvas.freeDrawingBrush.width = 3;
            fabricCanvas.freeDrawingBrush.color = "red";
        },
        "rect_btn": () => {
            currentTool = "rect";
            fabricCanvas.isDrawingMode = false;
        },
        "circle_btn": () => {
            currentTool = "circle";
            fabricCanvas.isDrawingMode = false;
        },
        "text_btn": () => {
            currentTool = "text";
            fabricCanvas.isDrawingMode = false;
        },
        "arrow_btn": () => {
            currentTool = "arrow";
            fabricCanvas.isDrawingMode = false;
        },
        "delete_btn": () => {
            const activeObjects = fabricCanvas.getActiveObjects();
            if (!activeObjects || activeObjects.length === 0) return;
            saveState();

            activeObjects.forEach(obj => {
                fabricCanvas.remove(obj);
            });

            fabricCanvas.discardActiveObject();
            fabricCanvas.requestRenderAll();
        },

        "clear_btn": () => {
            saveState();
            const objects = fabricCanvas.getObjects();
            objects.forEach(obj => {
                fabricCanvas.remove(obj);
            });
            fabricCanvas.discardActiveObject();
            fabricCanvas.requestRenderAll();
        },

        "undo_btn": () => undo(),
        "redo_btn": () => redo(),
        "close_btn": () => _closeEditor(),
    };

    for (const [id, func] of Object.entries(actions)) {
        const btn = document.getElementById(id);
        if (btn) btn.onclick = func;
    }
}

document.addEventListener("keydown", function(e) {
    if (e.key === "Delete" || e.key === "Backspace") {
        if (fabricCanvas && fabricCanvas.getActiveObject() &&
            fabricCanvas.getActiveObject().isEditing) {
            return;
        }
        const activeObjects = fabricCanvas?.getActiveObjects();
        if (!activeObjects || activeObjects.length === 0) return;
        saveState();
        activeObjects.forEach(obj => {
            fabricCanvas.remove(obj);
        });
        fabricCanvas.discardActiveObject();
        fabricCanvas.requestRenderAll();
    }

    if (e.key === "Escape") {
        const editor = document.getElementById("markup_editor");
        if (!editor || window.getComputedStyle(editor).display === "none") return;

        if (!_hasChanges) return;

        const modal = document.getElementById("markup_esc_modal");
        if (!modal) return;
        modal.style.display = "flex";

        // Wire Save → reuse mcr-submit click logic (sync comment then submitMarkup)
        document.getElementById("markup_esc_save").onclick = function() {
            modal.style.display = "none";
            const commentInner = document.getElementById("markup_comment_inner");
            const commentOrig = document.getElementById("markup_comment");
            if (commentInner && commentOrig) commentOrig.value = commentInner.value;
            submitMarkup();
        };

        // Wire Close → reuse close_btn logic
        document.getElementById("markup_esc_close").onclick = function() {
            modal.style.display = "none";
            const closeBtn = document.getElementById("close_btn");
            if (closeBtn) closeBtn.click();
        };
    }
});

function _reapplySnapshotBackground(callback) {
    if (!_currentSnapshotUrl || !fabricCanvas) return;
    fabric.Image.fromURL(_currentSnapshotUrl, function(img) {
        img.set({
            left: 0, top: 0,
            scaleX: _snapshotScale, scaleY: _snapshotScale,
            selectable: false, evented: false, excludeFromExport: true,
        });
        fabricCanvas.setBackgroundImage(img, function() {
            fabricCanvas.renderAll();
            if (callback) callback();
        });
    }, {crossOrigin: "anonymous"});
}

function _closeEditor() {
    _hasChanges = false;
    _editingMarkupId = null;
    _currentBaseImage = null;
    if (fabricCanvas) {
        _isLoadingJSON = true;
        fabricCanvas.clear();
        fabricCanvas.setBackgroundImage(null, fabricCanvas.renderAll.bind(fabricCanvas));
        _isLoadingJSON = false;
    }
    isSnapshotEditMode = false;
    _currentSnapshotUrl = null;
    _baseScreenshotData = null;
    _isLoadingJSON = false;
    undoStack = [];
    redoStack = [];
    currentTool = null;
    const commentTextarea = document.getElementById("markup_comment");
    if (commentTextarea) commentTextarea.value = "";
    document.getElementById("markup_editor").style.display = "none";
    _resetEditorControls();
    _setSidePanelsAbove(false);
}

function _handleCloseAttempt() {
    if (_hasChanges) {
        const modal = document.getElementById("markup_esc_modal");
        if (modal) {
            modal.style.display = "flex";

            document.getElementById("markup_esc_save").onclick = function () {
                modal.style.display = "none";
                const saveBtn = document.getElementById("mcr_save_existing_btn");
                if (_editingMarkupId && saveBtn) {
                    saveBtn.click();
                    return;
                }
                const commentInner = document.getElementById("markup_comment_inner");
                const commentOrig = document.getElementById("markup_comment");
                if (commentInner && commentOrig) commentOrig.value = commentInner.value;
                submitMarkup();
            };

            document.getElementById("markup_esc_close").onclick = function () {
                modal.style.display = "none";
                _closeEditor();
            };
            return;
        }
    }
    _closeEditor();
}

function initFabricEvents() {
    fabricCanvas.on("object:added", function() {
        if (_isLoadingJSON) return;
        if (!isRedoing) {
            saveState();
            _hasChanges = true;
        }
    });

    fabricCanvas.on("object:modified", function() {
        if (_isLoadingJSON) return;
        saveState();
        _hasChanges = true;
    });

    fabricCanvas.on("mouse:down", function(opt) {
        if (opt.target) return;
        const pointer = fabricCanvas.getPointer(opt.e);
        startX = pointer.x;
        startY = pointer.y;

        if (tempShape) return;

        if (currentTool === "rect") {
            tempShape = new fabric.Rect({
                left: startX, top: startY, width: 1, height: 1,
                fill: "transparent", stroke: "red", strokeWidth: 2,
            });
            fabricCanvas.add(tempShape);
        } else if (currentTool === "circle") {
            tempShape = new fabric.Circle({
                left: startX, top: startY, radius: 1,
                fill: "transparent", stroke: "blue", strokeWidth: 2,
            });
            fabricCanvas.add(tempShape);
        } else if (currentTool === "arrow") {
            // Create Line
            tempShape = new fabric.Line([startX, startY, startX, startY], {
                stroke: "red",
                strokeWidth: 3,
                selectable: false,
            });

            // Create Head (Invisible initially)
            tempShape._arrowHead = new fabric.Triangle({
                left: startX,
                top: startY,
                width: 20,
                height: 20,
                fill: "red",
                originX: "center",
                originY: "center",
                selectable: false,
                visible: false,
            });

            fabricCanvas.add(tempShape, tempShape._arrowHead);
        } else if (currentTool === "text") {
            const text = new fabric.IText("Text", {
                left: startX, top: startY, fontSize: 24,
                fill: "#000", backgroundColor: "#fff",
            });
            fabricCanvas.add(text);
            fabricCanvas.setActiveObject(text);
            text.enterEditing();
            currentTool = null;
        }
    });

    fabricCanvas.on("mouse:move", function(opt) {
        if (!tempShape) return;
        const pointer = fabricCanvas.getPointer(opt.e);
        const x = pointer.x;
        const y = pointer.y;

        if (currentTool === "rect") {
            tempShape.set({
                width: Math.abs(x - startX),
                height: Math.abs(y - startY),
                left: Math.min(x, startX),
                top: Math.min(y, startY),
            });
        } else if (currentTool === "circle") {
            tempShape.set({radius: Math.sqrt(Math.pow(x - startX, 2) + Math.pow(y - startY, 2)) / 2});
        } else if (currentTool === "arrow") {
            const angle = Math.atan2(y - startY, x - startX);
            const headLen = 15; // Adjusted for visual balance

            // Update line end point
            // We shorten the line slightly so it doesn't peak through the tip of the triangle
            const lineEndX = x - (headLen / 2) * Math.cos(angle);
            const lineEndY = y - (headLen / 2) * Math.sin(angle);

            tempShape.set({x2: lineEndX, y2: lineEndY});

            // Update Head position and rotation
            tempShape._arrowHead.set({
                left: x,
                top: y,
                angle: (angle * 180 / Math.PI) + 90,
                visible: true,
            });
        }
        fabricCanvas.requestRenderAll();
    });

    fabricCanvas.on("mouse:up", function() {
        if (tempShape) {
            if (currentTool === "arrow") {
                const arrowLine = tempShape;
                const arrowHead = tempShape._arrowHead;

                // Combine into a single group so they move together later
                const group = new fabric.Group([arrowLine, arrowHead], {
                    selectable: true,
                });

                fabricCanvas.remove(arrowLine, arrowHead);
                fabricCanvas.add(group);
                fabricCanvas.setActiveObject(group);
            } else {
                tempShape.set({selectable: true});
                tempShape.setCoords();
                fabricCanvas.setActiveObject(tempShape);
            }
        }
        tempShape = null;
        fabricCanvas.requestRenderAll();
    });
}

function submitMarkup() {
    const comment = document.getElementById("markup_comment").value;
    const threeCanvas = document.getElementById("odoo_canvas");

    const mergedCanvas = document.createElement("canvas");
    mergedCanvas.width = threeCanvas.width;
    mergedCanvas.height = threeCanvas.height;

    const ctx = mergedCanvas.getContext("2d");

    ctx.drawImage(threeCanvas, 0, 0);
    ctx.drawImage(fabricCanvas.lowerCanvasEl, 0, 0);

    const finalImage = mergedCanvas.toDataURL("image/png");

    let cleanBackground = null;

    if (_currentBaseImage) {
        cleanBackground = _currentBaseImage;
    } else if (_baseScreenshotData) {
        cleanBackground = _baseScreenshotData;
    } else {
        cleanBackground = threeCanvas.toDataURL("image/png");
    }

    const fabricJsonObj = fabricCanvas.toJSON();

    if (fabricJsonObj.backgroundImage) {
        delete fabricJsonObj.backgroundImage;
    }

    sendMarkupToBackend(
        finalImage,
        cleanBackground,
        comment,
        JSON.stringify(fabricJsonObj),
    );
}

function sendMarkupToBackend(imageData, baseImage, comment, canvasJson) {
    const container = document.getElementById("main_3d_web");
    const resId = container.dataset.resId;
    const resModel = container.dataset.resModel;
    let fileName = (container.dataset.fileName || "markup").replace(/\.[^/.]+$/, "") + ".jpg";

    const activityCheckbox = document.getElementById("activity_view");
    const scheduleActivity = activityCheckbox && activityCheckbox.checked;
    const dueDate = document.getElementById("mcr_due_date")?.value || "";
    const summary = document.getElementById("mcr_summary")?.value || "";
    const userId = parseInt(document.getElementById("mcr_user_id")?.value) || false;

    fetch("/plm/save_markup", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            jsonrpc: "2.0", method: "call",
            params: {
                image: imageData,
                base_image: baseImage,
                comment,
                filename: fileName,
                canvas_json: canvasJson,
                res_model: resModel,
                res_id: resId,
                schedule_activity: scheduleActivity,
                activity_due_date: dueDate,
                activity_summary: summary,
                activity_user_id: userId,
            },
        }),
    })
        .then(r => r.json())
        .then(data => {
            const newId = data.result?.markup_id || null;

            if (!scheduleActivity) {
                const displayComment = comment || (fileName + " - Markup Logged");
                addMarkupLog(baseImage, baseImage, displayComment, canvasJson, new Date().toLocaleDateString(), newId);
            }
            const commentTextarea = document.getElementById("markup_comment");
            if (commentTextarea) commentTextarea.value = "";
            if (activityCheckbox) activityCheckbox.checked = false;
            if (fabricCanvas) fabricCanvas.clear();

            undoStack = [];
            redoStack = [];
            currentTool = null;
            isSnapshotEditMode = false;
            _currentSnapshotUrl = null;
            _baseScreenshotData = null;

            const editor = document.getElementById("markup_editor");
            if (editor) editor.style.display = "none";
            _resetEditorControls();
            _setSidePanelsAbove(false);
        })
        .catch(err => console.error("Markup submit error:", err));
}

function initExistingMarkups() {
    if (_markupsInitialised) return;
    _markupsInitialised = true;

    const container = document.getElementById("main_3d_web");
    if (!container) return;
    const resId = container.dataset.resId;
    const resModel = container.dataset.resModel;
    if (!resId) {
        console.warn("initExistingMarkups: no resId found");
        return;
    }

    fetch("/plm/markup/load", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            jsonrpc: "2.0", method: "call",
            params: {res_id: parseInt(resId), res_model: resModel || ""},
        }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.result?.markups) {
                data.result.markups.reverse().forEach(m => {
                    const dateOnly = new Date(m.create_date).toLocaleDateString();
                    const snapshotUrl = m.snapshot
                        ? "data:image/jpeg;base64," + m.snapshot
                        : null;

                    const baseImageUrl = m.base_image
                        ? "data:image/jpeg;base64," + m.base_image
                        : null;

                    const canvasData = typeof m.canvas_data === "string" ? m.canvas_data : JSON.stringify(m.canvas_data);
                    const displayComment = m.comment || ((m.filename || "markup.jpg") + " - Markup Logged");
                    addMarkupLog(snapshotUrl, baseImageUrl, displayComment, canvasData, dateOnly, m.id);
                });
            }
        })
        .catch(err => console.error("Load error:", err));
}

function addMarkupLog(snapshotUrl, baseImageUrl, commentText, canvasJson, dateStr, markupId) {
    const logList = document.getElementById("markup_logs_list");
    if (!logList) return;

    if (markupId) {
        const existing = logList.querySelector(`[data-markup-id="${markupId}"]`);
        if (existing) return;
    }

    const placeholder = logList.querySelector("small");
    if (placeholder) placeholder.remove();

    const item = document.createElement("div");
    item.className = "markup_log_item";
    if (markupId) item.dataset.markupId = markupId;

    const eye = document.createElement("span");
    eye.className = "markup_log_eye fa fa-eye";
    eye.title = "View Screenshot";

    const label = document.createElement("span");
    label.className = "markup_log_label";
    label.textContent = dateStr + (commentText ? " - " + commentText : "");

    const edit = document.createElement("span");
    edit.className = "markup_log_load fa fa-pencil";
    edit.title = "Load into Editor";

    const del = document.createElement("span");
    del.className = "markup_log_delete fa fa-trash";
    del.title = "Delete";
    del.style.cursor = "pointer";
    del.style.marginLeft = "6px";
    del.style.color = "#a00";

    item.appendChild(eye);
    item.appendChild(label);
    item.appendChild(edit);
    item.appendChild(del);

    function onView(e) {
        e.stopPropagation();
        openMarkupLogModal(snapshotUrl || baseImageUrl, commentText, dateStr);
    }

    function onEdit(e) {
        e.stopPropagation();

        if (!baseImageUrl) {
            alert("Base image missing. Cannot edit.");
            return;
        }
        loadMarkupIntoEditor(canvasJson, baseImageUrl, markupId);
    }

    function onDelete(e) {
        e.stopPropagation();
        if (markupId) deleteMarkup(markupId, item);
    }

    function onRowClick() {
        openMarkupLogModal(snapshotUrl || baseImageUrl, commentText, dateStr);
    }

    eye.addEventListener("click", onView);
    edit.addEventListener("click", onEdit);
    del.addEventListener("click", onDelete);
    item.addEventListener("click", onRowClick);
    item.dataset.comment = commentText || "";
    item.dataset.date = dateStr || "";

    logList.prepend(item);
}

function loadMarkupIntoEditor(canvasJson, bgUrl, markupId = null) {
    _editingMarkupId = markupId;
    _currentBaseImage = bgUrl;

    if (!bgUrl) {
        alert("No editable data found.");
        return;
    }

    if (bgUrl && !bgUrl.startsWith("data:image")) {
        bgUrl = "data:image/png;base64," + bgUrl;
    }

    console.log("bgUrl preview:", bgUrl.substring(0, 100));

    const myGen = ++_loadGeneration;

    openMarkupEditor();

    isSnapshotEditMode = false;
    _currentSnapshotUrl = null;

    _isLoadingJSON = true;

    if (fabricCanvas) {
        fabricCanvas.discardActiveObject();
        fabricCanvas.clear();

        fabricCanvas.backgroundImage = null;
        fabricCanvas.setOverlayImage(null, fabricCanvas.renderAll.bind(fabricCanvas));
    }

    undoStack = [];
    redoStack = [];

    fabricCanvas.renderOnAddRemove = false;
    let parsed = null;

    if (canvasJson) {
        parsed = typeof canvasJson === "string"
            ? JSON.parse(canvasJson)
            : canvasJson;

        if (parsed.backgroundImage) {
            delete parsed.backgroundImage;
        }
    }

    fabricCanvas.loadFromJSON(parsed || {}, function() {
        if (myGen !== _loadGeneration) return;

        fabric.Image.fromURL(
            bgUrl,
            function(img) {
                if (myGen !== _loadGeneration) return;

                if (!img) {
                    console.error("❌ Image failed to load");
                    return;
                }

                const canvasW = fabricCanvas.getWidth();
                const canvasH = fabricCanvas.getHeight();

                const scale = Math.min(canvasW / img.width, canvasH / img.height);

                img.set({
                    left: 0,
                    top: 0,
                    originX: "left",
                    originY: "top",
                    scaleX: scale,
                    scaleY: scale,
                    selectable: false,
                    evented: false,
                    excludeFromExport: true,
                });
                fabricCanvas.backgroundImage = img;

                _isLoadingJSON = false;

                fabricCanvas.renderOnAddRemove = true;
                fabricCanvas.requestRenderAll();

                saveState();
            },
            {
                crossOrigin: "anonymous",
                onError: function() {
                    console.error("Failed to load base image");
                },
            },
        );
    });
}

window.loadMarkupIntoEditor = loadMarkupIntoEditor;

function openMarkupLogModal(imageUrl, commentText, dateStr) {
    const modal = document.getElementById("markup_log_modal");
    if (!modal) return;
    document.getElementById("markup_log_modal_date").textContent = dateStr;
    document.getElementById("markup_log_modal_img").src = imageUrl;
    document.getElementById("markup_log_modal_comment").textContent = commentText || "";
    modal.classList.add("open");
}

window.addEventListener("load", function() {
    const modal = document.getElementById("markup_esc_modal");
    const closeIcon = document.getElementById("markup_log_modal_close2");
    if (closeIcon) {
        closeIcon.addEventListener("click", () => {
            modal.style.display = "none";
        });
    }
});

window.addEventListener("load", function() {
    const closeBtn = document.getElementById("markup_log_modal_close");
    if (closeBtn) closeBtn.addEventListener("click", () => document.getElementById("markup_log_modal").classList.remove("open"));
    const modal = document.getElementById("markup_log_modal");
    if (modal) modal.addEventListener("click", e => {
        if (e.target === modal) modal.classList.remove("open");
    });
});

let toastOffset = 0;

function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `custom-toast ${type}`;
    toast.textContent = message;
    toastOffset += 70;
    toast.style.top = `${toastOffset}px`;
    document.body.appendChild(toast);
    requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("show")));
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => {
            toast.remove();
            toastOffset = Math.max(0, toastOffset - 70);
        }, 300);
    }, 3500);
}

function deleteMarkup(markupId, itemElement) {
    fetch("/plm/markup/delete", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({jsonrpc: "2.0", method: "call", params: {markup_id: markupId}}),
    })
        .then(r => r.json())
        .then(data => {
            if (data.result?.success) {
                itemElement.remove();
                const logList = document.getElementById("markup_logs_list");
                if (logList && logList.children.length === 0) {
                    const empty = document.createElement("small");
                    empty.textContent = "No markups yet.";
                    logList.appendChild(empty);
                }
            } else {
                showToast("You are not allowed to delete this markup.", "warning");
            }
        })
        .catch(err => {
            console.error("Delete error:", err);
            showToast("Something went wrong while deleting.", "danger");
        });
}

window.addEventListener("load", function() {
    function rpcCall(model, method, args, kwargs) {
        return fetch("/web/dataset/call_kw", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({jsonrpc: "2.0", method: "call", params: {model, method, args, kwargs: kwargs || {}}}),
        }).then(r => r.json()).then(data => {
            if (data.error) throw new Error(data.error.data.message || "RPC Error");
            return data.result;
        });
    }

    function getToDoActivityTypeId() {
        return rpcCall("mail.activity.type", "search_read", [[["name", "ilike", "to"]]], {
            fields: ["id", "name"],
            limit: 5,
        })
            .then(results => {
                if (results?.length) {
                    const e = results.find(r => r.name.toLowerCase().replace("-", "").includes("todo"));
                    return e ? e.id : results[0].id;
                }
                return 1;
            });
    }

    function loadActivityUsers() {
        const select = document.getElementById("activity_user_id");
        if (!select) return;
        rpcCall("res.users", "search_read", [[["share", "=", false], ["active", "=", true]]], {
            fields: ["id", "name"],
            order: "name asc",
            limit: 100,
        })
            .then(users => {
                select.innerHTML = "";
                users.forEach(u => {
                    const o = document.createElement("option");
                    o.value = u.id;
                    o.textContent = u.name;
                    select.appendChild(o);
                });
                if (window.odoo?.session_info?.uid) select.value = odoo.session_info.uid;
            })
            .catch(() => {
                select.innerHTML = "<option value=\"\">Error loading users</option>";
            });
    }

    function showActivityMsg(text, color) {
        const el = document.getElementById("activity_msg");
        if (!el) return;
        el.textContent = text;
        el.style.color = color;
        el.style.display = "block";
    }

    function resetActivityForm() {
        const today = new Date().toISOString().split("T")[0];
        ["activity_due_date", "activity_summary", "activity_note"].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = id === "activity_due_date" ? today : "";
        });
        const mg = document.getElementById("activity_msg");
        if (mg) mg.style.display = "none";
    }

    let usersLoaded = false;
    const activityViewBtn = document.getElementById("activity_view");
    const activityPanel = document.getElementById("activity_form_panel");
    if (activityViewBtn && activityPanel) {
        activityViewBtn.addEventListener("click", function() {
            const isOpen = activityPanel.style.display !== "none";
            activityPanel.style.display = isOpen ? "none" : "block";
            if (!isOpen) {
                resetActivityForm();
                if (!usersLoaded) {
                    loadActivityUsers();
                    usersLoaded = true;
                }
            }
        });
    }

    const cancelBtn = document.getElementById("activity_cancel_btn");
    if (cancelBtn) cancelBtn.addEventListener("click", () => {
        if (activityPanel) activityPanel.style.display = "none";
    });

    const submitBtn2 = document.getElementById("activity_submit_btn");
    if (submitBtn2) {
        submitBtn2.addEventListener("click", function() {
            const container = document.getElementById("main_3d_web");
            const resId = container ? parseInt(container.dataset.resId) : null;
            const dueDate = document.getElementById("activity_due_date")?.value || "";
            const summary = document.getElementById("activity_summary")?.value || "";
            const note = document.getElementById("activity_note")?.value || "";
            const userId = parseInt(document.getElementById("activity_user_id")?.value) || false;
            if (!dueDate) {
                showActivityMsg("Please set a due date.", "orange");
                return;
            }
            if (!resId) {
                showActivityMsg("Could not determine document ID.", "orange");
                return;
            }
            getToDoActivityTypeId()
                .then(activityTypeId =>
                    rpcCall("ir.model", "search_read", [[["model", "=", "ir.attachment"]]], {fields: ["id"], limit: 1})
                        .then(models => {
                            if (!models?.length) throw new Error("ir.model not found");
                            return rpcCall("mail.activity", "create", [{
                                res_model_id: models[0].id,
                                res_id: resId,
                                activity_type_id: activityTypeId,
                                date_deadline: dueDate,
                                summary: summary || "",
                                note: note || "",
                                user_id: userId || false,
                            }]);
                        }),
                )
                .then(() => {
                    showActivityMsg("Activity scheduled!", "#00a09d");
                    setTimeout(() => {
                        if (activityPanel) activityPanel.style.display = "none";
                        resetActivityForm();
                    }, 1800);
                })
                .catch(err => {
                    showActivityMsg(err.message, "tomato");
                    console.error(err);
                });
        });
    }
});

window.addEventListener("load", function() {
    const params = new URLSearchParams(window.location.search);
    const markupId = params.get("markup_id");
    if (!markupId) return;

    fetch("/plm_web_3d/markup/addon", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {markup_id: parseInt(markupId)},
        }),
    })
        .then(r => r.json())
        .then(data => {
            const m = data.result?.markup;
            if (!m) return;

            let bgUrl = null;
            if (m.base_image) {
                bgUrl = "data:image/jpeg;base64," + m.base_image;
            } else {
                bgUrl = m.snapshot ? "data:image/jpeg;base64," + m.snapshot : null;
            }

            const canvasData = typeof m.canvas_data === "string"
                ? m.canvas_data
                : JSON.stringify(m.canvas_data);

            setTimeout(() => {
                loadMarkupIntoEditor(canvasData, bgUrl, parseInt(markupId));
            }, 300);
        })
        .catch(err => console.error("Auto-load markup error:", err));
});

function _reapplyBaseBackground(callback) {
    if (!_currentBaseImage || !fabricCanvas) return;

    fabric.Image.fromURL(_currentBaseImage, function(img) {

        const canvasW = fabricCanvas.getWidth();
        const canvasH = fabricCanvas.getHeight();

        const scale = Math.min(canvasW / img.width, canvasH / img.height);

        img.set({
            left: 0,
            top: 0,
            originX: "left",
            originY: "top",
            scaleX: scale,
            scaleY: scale,
            selectable: false,
            evented: false,
            excludeFromExport: true,
        });

        fabricCanvas.setBackgroundImage(img, function() {
            fabricCanvas.renderAll();
            if (callback) callback();
        });

    }, {crossOrigin: "anonymous"});
}
