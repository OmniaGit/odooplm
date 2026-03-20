/** @odoo-module **/

let fabricCanvas = null;
let currentTool = null;
let startX, startY;
let tempShape = null;
let undoStack = [];
let redoStack = [];
let isRedoing = false;
// Track whether editor was opened from a saved snapshot (edit mode)
let isSnapshotEditMode = false;

window.addEventListener("load", () => {
    const markupBtn = document.getElementById("markup_button");
    if (markupBtn) {
        markupBtn.addEventListener("click", openMarkupEditor);
    }
});

window.addEventListener("load", function () {
    const submitBtn = document.getElementById("submit_markup");
    if (submitBtn) {
        submitBtn.addEventListener("click", submitMarkup);
    }
    initExistingMarkups();
});

function _positionEditorControls(tRect) {
    const editor = document.getElementById("markup_editor");
    if (!editor) return;

    var toolbar    = document.getElementById("markup_toolbar");
    var commentBox = document.getElementById("markup_comment_box");
    if (toolbar)    toolbar.style.display = "none";
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

        var origBtns  = toolbar.querySelectorAll("button");
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
    commentInput.id          = "markup_comment_inner";
    commentInput.type        = "text";
    commentInput.placeholder = "Write Message...";
    commentInput.className   = "mcr-input";

    // Activity panel — built fresh (not cloned) to avoid dark inline styles from HTML
    var activityPanelClone = document.createElement("div");
    activityPanelClone.id        = "mcr_activity_panel";
    activityPanelClone.className = "mcr-activity-panel";
    activityPanelClone.style.display = "none";

    var today = new Date().toISOString().split("T")[0];

    activityPanelClone.innerHTML =
        '<div class="mcr-ap-row">' +
            '<label class="mcr-ap-label">Due Date</label>' +
            '<input type="date" id="mcr_due_date" class="mcr-ap-input" value="' + today + '"/>' +
        '</div>' +
        '<div class="mcr-ap-row">' +
            '<label class="mcr-ap-label">Summary</label>' +
            '<input type="text" id="mcr_summary" class="mcr-ap-input" placeholder="Summary"/>' +
        '</div>' +
        '<div class="mcr-ap-row">' +
            '<label class="mcr-ap-label">Assigned To</label>' +
            '<select id="mcr_user_id" class="mcr-ap-input"><option value="">Loading users...</option></select>' +
        '</div>';

    // Load users into the cloned select
    fetch("/web/dataset/call_kw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0", method: "call",
            params: {
                model: "res.users", method: "search_read",
                args: [[["share","=",false],["active","=",true]]],
                kwargs: { fields: ["id","name"], order: "name asc", limit: 100 }
            }
        })
    })
    .then(function(r) { return r.json(); })
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
        if (sel) sel.innerHTML = '<option value="">Error loading users</option>';
    });

    // Activity checkbox
    var activityLabel = document.createElement("label");
    activityLabel.className = "mcr-activity-label";
    activityLabel.title     = "Schedule Activity";

    var activityCheck = document.createElement("input");
    activityCheck.type      = "checkbox";
    activityCheck.className = "mcr-activity-check";
    activityCheck.onchange  = function() {
        // Sync to original hidden checkbox
        var orig = document.getElementById("activity_view");
        if (orig) {
            orig.checked = this.checked;
            orig.dispatchEvent(new Event("change"));
        }
        // Show/hide the cloned panel above comment row
        if (activityPanelClone) {
            activityPanelClone.style.display = this.checked ? "block" : "none";
        }
    };

    activityLabel.appendChild(activityCheck);

    var submitBtn = document.createElement("button");
    submitBtn.textContent = "Submit";
    submitBtn.className   = "mcr-submit";
    submitBtn.onclick = function(e) {
        e.stopPropagation();
        var orig = document.getElementById("markup_comment");
        if (orig) orig.value = commentInput.value;
        submitMarkup();
    };

    commentRow.appendChild(commentInput);
    commentRow.appendChild(activityLabel);
    commentRow.appendChild(submitBtn);

    // Sub-container keeps activity panel directly above comment row (aligned together)
    var commentGroup = document.createElement("div");
    commentGroup.className = "mcr-comment-group";
    if (activityPanelClone) commentGroup.appendChild(activityPanelClone);
    commentGroup.appendChild(commentRow);

    wrap.appendChild(commentGroup);
    editor.appendChild(wrap);
}

function _resetEditorControls() {
    var row = document.getElementById("markup_controls_row");
    if (row && row.parentNode) row.parentNode.removeChild(row);
    var toolbar    = document.getElementById("markup_toolbar");
    var commentBox = document.getElementById("markup_comment_box");
    if (toolbar)    toolbar.style.display = "none";
    if (commentBox) commentBox.style.display = "none";
}


function _setSidePanelsAbove(above) {
    var container = document.getElementById("main_3d_web");
    if (!container) return;
    // Only raise z-index — never touch position, which would break absolute-positioned panels
    Array.from(container.children).forEach(function(child) {
        if (child.id !== "markup_editor" && child.id !== "odoo_canvas") {
            child.style.zIndex = above ? "200" : "";
        }
    });
}

function openMarkupEditor() {
    const editor      = document.getElementById("markup_editor");
    const threeCanvas = document.getElementById("odoo_canvas");
    const container   = document.getElementById("main_3d_web");
    if (!editor || !threeCanvas || !container) return;

    container.style.position = "relative";

    const tRect = threeCanvas.getBoundingClientRect();
    const cRect = container.getBoundingClientRect();

    const left = tRect.left - cRect.left;
    const top  = tRect.top  - cRect.top;
    const w    = tRect.width;
    const h    = tRect.height;

    editor.style.cssText = [
        "display: block",
        "position: absolute",
        "left: "   + left + "px",
        "top: "    + top  + "px",
        "width: "  + w    + "px",
        "height: " + h    + "px",
        "margin: 0",
        "padding: 0",
        "overflow: hidden",
        "z-index: 100",
        "pointer-events: auto",
        "box-sizing: border-box"
    ].join(";");

    _positionEditorControls(tRect);
    _setSidePanelsAbove(true);

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
}

function resizeCanvas() {
    const threeCanvas = document.getElementById("odoo_canvas");
    if (!threeCanvas || !fabricCanvas) return;
    fabricCanvas.setWidth(threeCanvas.clientWidth);
    fabricCanvas.setHeight(threeCanvas.clientHeight);
}

function saveState() {
    if (isRedoing) return;
    undoStack.push(JSON.stringify(fabricCanvas));
    redoStack = [];
}

function undo() {
    if (undoStack.length > 0) {
        isRedoing = true;
        redoStack.push(JSON.stringify(fabricCanvas));
        const lastState = undoStack.pop();
        fabricCanvas.loadFromJSON(lastState, function () {
            fabricCanvas.renderAll();
            isRedoing = false;
        });
    }
}

function redo() {
    if (redoStack.length > 0) {
        isRedoing = true;
        undoStack.push(JSON.stringify(fabricCanvas));
        const nextState = redoStack.pop();
        fabricCanvas.loadFromJSON(nextState, function () {
            fabricCanvas.renderAll();
            isRedoing = false;
        });
    }
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
        "clear_btn": () => {
            saveState();
            fabricCanvas.clear();
            // If in snapshot mode, re-apply snapshot background after clear
            if (isSnapshotEditMode) {
                _reapplySnapshotBackground();
            }
        },
        "undo_btn": () => undo(),
        "redo_btn": () => redo(),
        "close_btn": () => {
            _closeEditor();
        },
    };
    for (const [id, func] of Object.entries(actions)) {
        const btn = document.getElementById(id);
        if (btn) btn.onclick = func;
    }
}

// ─── Internal helpers ───────────────────────────────────────────────────────

let _currentSnapshotUrl = null;
let _snapshotScale = 1; // uniform scale — set once when snapshot is first loaded

function _reapplySnapshotBackground(callback) {
    if (!_currentSnapshotUrl || !fabricCanvas) return;
    fabric.Image.fromURL(_currentSnapshotUrl, function (img) {
        // Use the pre-computed uniform scale (set in loadMarkupIntoEditor).
        // Never recalculate per-axis here — that would cause stretch on re-apply.
        img.set({
            left: 0,
            top: 0,
            scaleX: _snapshotScale,
            scaleY: _snapshotScale,
            selectable: false,
            evented: false,
            excludeFromExport: true
        });
        fabricCanvas.setBackgroundImage(img, function () {
            fabricCanvas.renderAll();
            if (callback) callback();
        });
    }, { crossOrigin: 'anonymous' });
}

function _closeEditor() {
    if (fabricCanvas) {
        fabricCanvas.clear();
        fabricCanvas.setBackgroundImage(null, fabricCanvas.renderAll.bind(fabricCanvas));
    }

    isSnapshotEditMode = false;
    _currentSnapshotUrl = null;

    undoStack = [];
    redoStack = [];
    currentTool = null;
    const commentTextarea = document.getElementById("markup_comment");
    if (commentTextarea) commentTextarea.value = "";
    document.getElementById("markup_editor").style.display = "none";
    _resetEditorControls();
    _setSidePanelsAbove(false);
}

// ────────────────────────────────────────────────────────────────────────────

function initFabricEvents() {
    fabricCanvas.on("object:added", () => {
        if (!isRedoing) saveState();
    });

    fabricCanvas.on("object:modified", () => {
        saveState();
    });

    fabricCanvas.on("mouse:down", function (opt) {
        if (opt.target) return;
        const pointer = fabricCanvas.getPointer(opt.e);
        startX = pointer.x;
        startY = pointer.y;
        if (tempShape) return;
        if (currentTool === "rect") {
            tempShape = new fabric.Rect({
                left: startX,
                top: startY,
                width: 1,
                height: 1,
                fill: "transparent",
                stroke: "red",
                strokeWidth: 2
            });
            fabricCanvas.add(tempShape);
        }
        else if (currentTool === "circle") {
            tempShape = new fabric.Circle({
                left: startX,
                top: startY,
                radius: 1,
                fill: "transparent",
                stroke: "blue",
                strokeWidth: 2
            });
            fabricCanvas.add(tempShape);
        }
        else if (currentTool === "arrow") {
            const pointer = fabricCanvas.getPointer(opt.e);
            startX = pointer.x;
            startY = pointer.y;
            tempShape = new fabric.Path(`M ${startX} ${startY} L ${startX} ${startY}`, {
                stroke: '#fff',
                strokeWidth: 2,
                fill: 'red',
                selectable: false,
                objectCaching: false
            });
            fabricCanvas.add(tempShape);
        }
        else if (currentTool === "text") {
            const text = new fabric.IText("Text", {
                left: startX,
                top: startY,
                fontSize: 24,
                fill: "#000",
                backgroundColor: "#fff"
            });
            fabricCanvas.add(text);
            fabricCanvas.setActiveObject(text);
            text.enterEditing();
            currentTool = null;
        }
    });

    fabricCanvas.on("mouse:move", function (opt) {
        if (!tempShape) return;
        const pointer = fabricCanvas.getPointer(opt.e);
        if (currentTool === "rect") {
            tempShape.set({
                width: pointer.x - startX,
                height: pointer.y - startY
            });
        }
        else if (currentTool === "circle") {
            const radius = Math.sqrt(Math.pow(pointer.x - startX, 2) + Math.pow(pointer.y - startY, 2));
            tempShape.set({ radius: radius });
        }
        else if (currentTool === "arrow") {
            const headLength = 20;
            const shaftWidth = 10;
            const headWidth = 24;
            const angle = Math.atan2(pointer.y - startY, pointer.x - startX);
            const x0 = startX, y0 = startY;
            const x1 = pointer.x, y1 = pointer.y;
            const tX = x1 - headLength * Math.cos(angle);
            const tY = y1 - headLength * Math.sin(angle);
            const p1x = tX + (headWidth / 2) * Math.cos(angle + Math.PI / 2);
            const p1y = tY + (headWidth / 2) * Math.sin(angle + Math.PI / 2);
            const p2x = tX + (headWidth / 2) * Math.cos(angle - Math.PI / 2);
            const p2y = tY + (headWidth / 2) * Math.sin(angle - Math.PI / 2);
            const s1x = tX + (shaftWidth / 2) * Math.cos(angle + Math.PI / 2);
            const s1y = tY + (shaftWidth / 2) * Math.sin(angle + Math.PI / 2);
            const s2x = tX + (shaftWidth / 2) * Math.cos(angle - Math.PI / 2);
            const s2y = tY + (shaftWidth / 2) * Math.sin(angle - Math.PI / 2);
            const tail1x = x0 + (shaftWidth / 2) * Math.cos(angle + Math.PI / 2);
            const tail1y = y0 + (shaftWidth / 2) * Math.sin(angle + Math.PI / 2);
            const tail2x = x0 + (shaftWidth / 2) * Math.cos(angle - Math.PI / 2);
            const tail2y = y0 + (shaftWidth / 2) * Math.sin(angle - Math.PI / 2);
            const pathData = `M ${tail1x},${tail1y} L ${s1x},${s1y} L ${p1x},${p1y} L ${x1},${y1} L ${p2x},${p2y} L ${s2x},${s2y} L ${tail2x},${tail2y} Z`;
            tempShape.set({ path: new fabric.Path(pathData).path });
        }
        fabricCanvas.renderAll();
    });

    fabricCanvas.on("mouse:up", function () {
        if (tempShape) {
            tempShape.set({
                selectable: true
            });
            fabricCanvas.setActiveObject(tempShape);
            tempShape.setCoords();
        }
        tempShape = null;
    });
}

function saveMarkupWithBackground() {
    const viewer      = document.getElementById("main_3d_web");
    const threeCanvas = document.getElementById("odoo_canvas");
    let fileName = (viewer.dataset.fileName || "markup").replace(/\.[^/.]+$/, "") + ".jpg";

    const fW = threeCanvas.clientWidth;
    const fH = threeCanvas.clientHeight;

    const bgImg = new Image();
    bgImg.onload = function () {
        const tmp = document.createElement("canvas");
        tmp.width  = fW;
        tmp.height = fH;
        const ctx = tmp.getContext("2d");
        ctx.drawImage(bgImg, 0, 0, fW, fH);

        const markupImg = new Image();
        markupImg.onload = function () {
            ctx.drawImage(markupImg, 0, 0, fW, fH);
            const link = document.createElement("a");
            link.href = tmp.toDataURL("image/jpeg");
            link.download = fileName;
            link.click();
        };
        markupImg.src = fabricCanvas.toDataURL({ format: "png" });
    };
    bgImg.src = threeCanvas.toDataURL("image/jpeg");
}

function submitMarkup() {
    const comment = document.getElementById("markup_comment").value;

    if (isSnapshotEditMode && _currentSnapshotUrl) {
        const snapshotImg = new Image();
        snapshotImg.crossOrigin = "anonymous";
        snapshotImg.onload = function () {
            const fW = fabricCanvas.getWidth();
            const fH = fabricCanvas.getHeight();
            const tmp = document.createElement("canvas");
            tmp.width  = fW;
            tmp.height = fH;
            const ctx = tmp.getContext("2d");
            ctx.drawImage(snapshotImg, 0, 0, fW, fH);

            const markupImg = new Image();
            markupImg.onload = function () {
                ctx.drawImage(markupImg, 0, 0, fW, fH);
                sendMarkupToBackend(tmp.toDataURL("image/jpeg"), comment, JSON.stringify(fabricCanvas.toJSON()));
            };
            markupImg.src = fabricCanvas.toDataURL({ format: "png" });
        };
        snapshotImg.src = _currentSnapshotUrl;
        return;
    }

    const threeCanvas = document.getElementById("odoo_canvas");
    const fW = threeCanvas.clientWidth;
    const fH = threeCanvas.clientHeight;

    const bgImg = new Image();
    bgImg.onload = function () {
        const tmp = document.createElement("canvas");
        tmp.width  = fW;
        tmp.height = fH;
        const ctx = tmp.getContext("2d");
        ctx.drawImage(bgImg, 0, 0, fW, fH);

        const markupImg = new Image();
        markupImg.onload = function () {
            ctx.drawImage(markupImg, 0, 0, fW, fH);
            sendMarkupToBackend(tmp.toDataURL("image/jpeg"), comment, JSON.stringify(fabricCanvas.toJSON()));
        };
        markupImg.src = fabricCanvas.toDataURL({ format: "png" });
    };
    bgImg.src = threeCanvas.toDataURL("image/jpeg");
}


function _scheduleActivity(resId, dueDate, summary, userId, note, imageData) {
    function rpc(model, method, args, kwargs) {
        return fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0", method: "call",
                params: { model, method, args, kwargs: kwargs || {} }
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error.data.message || "RPC Error");
            return data.result;
        });
    }

    // Step 1: Upload markup image as ir.attachment (if available)
    var imageUploadPromise = Promise.resolve(null);
    if (imageData) {
        var b64 = imageData.replace(/^data:image\/\w+;base64,/, "");
        imageUploadPromise = rpc("ir.attachment", "create", [{
            name:     "markup_" + new Date().toISOString().slice(0,10) + ".jpg",
            type:     "binary",
            datas:    b64,
            res_model: "ir.attachment",
            res_id:   resId
        }]).catch(function() { return null; });
    }

    return imageUploadPromise.then(function(attachmentId) {
        // Build note HTML — include comment + inline image preview
        var noteHtml = note ? "<p>" + note + "</p>" : "";
        if (attachmentId) {
            noteHtml += '<p><img src="/web/image/ir.attachment/' + attachmentId + '/datas" style="max-width:400px;border-radius:4px;margin-top:4px;" alt="Markup"/></p>';
        }

        return rpc("mail.activity.type", "search_read",
            [[["name", "ilike", "to"]]],
            { fields: ["id", "name"], limit: 5 }
        ).then(results => {
            const exact = results?.find(r => r.name.toLowerCase().replace("-","").includes("todo"));
            return exact ? exact.id : (results?.[0]?.id || 1);
        }).then(activityTypeId => {
            return rpc("ir.model", "search_read",
                [[["model", "=", "ir.attachment"]]],
                { fields: ["id"], limit: 1 }
            ).then(models => {
                if (!models?.length) throw new Error("ir.model not found");
                var activityVals = {
                    res_model_id:     models[0].id,
                    res_id:           resId,
                    activity_type_id: activityTypeId,
                    date_deadline:    dueDate,
                    summary:          summary || "",
                    note:             noteHtml,
                    user_id:          userId  || false
                };
                return rpc("mail.activity", "create", [activityVals]);
            });
        });
    });
}

function sendMarkupToBackend(imageData, comment, canvasJson) {
    const container = document.getElementById("main_3d_web");

    const resId = container.dataset.resId;
    const resModel = container.dataset.resModel;

    let fileName = container.dataset.fileName || "markup";
    fileName = fileName.replace(/\.[^/.]+$/, "") + ".jpg";

    console.log("SENDING:", resId, resModel);

    const activityCheckbox = document.getElementById("activity_view");
    const scheduleActivity = activityCheckbox && activityCheckbox.checked;

    const dueDate = document.getElementById("mcr_due_date")?.value || "";
    const summary = document.getElementById("mcr_summary")?.value || "";
    const userId  = parseInt(document.getElementById("mcr_user_id")?.value) || false;

    console.log("SUMMARY SENT:", summary);

    fetch("/plm_web_3d/save_markup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {
                image: imageData,
                comment: comment,
                filename: fileName,
                canvas_json: canvasJson,
                res_model: resModel,
                res_id: resId,
                schedule_activity: scheduleActivity,


                activity_due_date: dueDate,
                activity_summary: summary,
                activity_user_id: userId
            }
        })
    })
    .then(r => r.json())
    .then(() => {

        if (!scheduleActivity) {
            addMarkupLog(imageData, comment, canvasJson, new Date().toLocaleDateString());
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

        const editor = document.getElementById("markup_editor");
        if (editor) editor.style.display = "none";

        _resetEditorControls();
        _setSidePanelsAbove(false);
    })
    .catch(err => {
        console.error("Markup submit error:", err);
    });
}

// Log Tracking Function  -----------------
function initExistingMarkups() {
    const container = document.getElementById("main_3d_web");
    if (!container) return;

    const resId    = container.dataset.resId;
    const resModel = container.dataset.resModel;

    if (!resId) {
        console.warn("initExistingMarkups: no resId found");
        return;
    }

    fetch("/plm/markup/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {
                res_id:    parseInt(resId),
                res_model: resModel || ""
            }
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.result?.markups) {
            data.result.markups.reverse().forEach(m => {
                const dateOnly   = new Date(m.create_date).toLocaleDateString();
                const snapshot   = m.snapshot ? "data:image/jpeg;base64," + m.snapshot : null;
                const canvasData = typeof m.canvas_data === "string"
                    ? m.canvas_data
                    : JSON.stringify(m.canvas_data);
                addMarkupLog(snapshot, m.comment, canvasData, dateOnly, m.id);
            });
        }
    })
    .catch(err => console.error("Load error:", err));
}

function addMarkupLog(screenshotDataUrl, commentText, canvasJson, dateStr, markupId) {
    const logList = document.getElementById("markup_logs_list");
    if (!logList) return;

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

    item.addEventListener("click", function () {
        openMarkupLogModal(screenshotDataUrl, commentText, dateStr);
    });

    eye.addEventListener("click", function (e) {
        e.stopPropagation();
        openMarkupLogModal(screenshotDataUrl, commentText, dateStr);
    });

    edit.addEventListener("click", function (e) {
        e.stopPropagation();
        loadMarkupIntoEditor(canvasJson, screenshotDataUrl);
    });

    del.addEventListener("click", function (e) {
        e.stopPropagation();
        if (markupId) {
            deleteMarkup(markupId, item);
        }
    });

    logList.prepend(item);
}

function deleteMarkup(markupId, itemElement) {
    if (!confirm("Delete this markup?")) return;

    fetch("/plm/markup/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: { markup_id: markupId }
        })
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
        }
    })
    .catch(err => console.error("Delete error:", err));
}

function loadMarkupIntoEditor(canvasJson, snapshotUrl) {
    if (!snapshotUrl && !canvasJson) {
        alert("No saved state found for this log.");
        return;
    }

    if (snapshotUrl) {
        isSnapshotEditMode = true;
        _currentSnapshotUrl = snapshotUrl;

        fabric.Image.fromURL(snapshotUrl, function (img) {
            const threeCanvas = document.getElementById("odoo_canvas");
            const container   = document.getElementById("main_3d_web");
            const cRect = container.getBoundingClientRect();
            const tRect = threeCanvas.getBoundingClientRect();

            // Editor covers exactly the odoo_canvas area
            const left = tRect.left - cRect.left;
            const top  = tRect.top  - cRect.top;
            const editorW = tRect.width;
            const editorH = tRect.height;

            const editor = document.getElementById("markup_editor");
            if (editor) {
                container.style.position = "relative";
                editor.style.cssText = [
                    "display: block",
                    "position: absolute",
                    "left: "   + left    + "px",
                    "top: "    + top     + "px",
                    "width: "  + editorW + "px",
                    "height: " + editorH + "px",
                    "margin: 0",
                    "padding: 0",
                    "overflow: hidden",
                    "z-index: 100",
                    "pointer-events: auto",
                    "box-sizing: border-box"
                ].join(";");
                _positionEditorControls(tRect);
                _setSidePanelsAbove(true);
            }

            if (!fabricCanvas) {
                fabricCanvas = new fabric.Canvas("markup_canvas");
                initFabricEvents();
                initToolbar();
            }

            // Scale fabric canvas to fill the editor display area exactly.
            // The snapshot is scaled uniformly to fit — scaleX/Y applied to background image.
            const scaleX = editorW / img.width;
            const scaleY = editorH / img.height;
            _snapshotScale = Math.min(scaleX, scaleY);

            fabricCanvas.setWidth(editorW);
            fabricCanvas.setHeight(editorH);

            fabricCanvas.clear();

            img.set({
                left: 0,
                top: 0,
                scaleX: scaleX,
                scaleY: scaleY,
                selectable: false,
                evented: false,
                excludeFromExport: true
            });

            fabricCanvas.setBackgroundImage(img, function () {
                fabricCanvas.renderAll();
                undoStack = [];
                redoStack = [];
                saveState();
            });

        }, { crossOrigin: 'anonymous' });

    } else {
        openMarkupEditor();
        fabricCanvas.loadFromJSON(canvasJson, function () {
            fabricCanvas.renderAll();
            saveState();
        });
    }
}


function openMarkupLogModal(screenshotDataUrl, commentText, dateStr) {
    const modal = document.getElementById("markup_log_modal");
    if (!modal) return;
    document.getElementById("markup_log_modal_date").textContent = dateStr;
    document.getElementById("markup_log_modal_img").src = screenshotDataUrl;
    document.getElementById("markup_log_modal_comment").textContent = commentText || "";
    modal.classList.add("open");
}

window.addEventListener("load", function () {
    const closeBtn = document.getElementById("markup_log_modal_close");
    if (closeBtn) {
        closeBtn.addEventListener("click", function () {
            document.getElementById("markup_log_modal").classList.remove("open");
        });
    }
    const modal = document.getElementById("markup_log_modal");
    if (modal) {
        modal.addEventListener("click", function (e) {
            if (e.target === modal) modal.classList.remove("open");
        });
    }
});


// Activity Panel -----------------

window.addEventListener("load", function () {

    function rpcCall(model, method, args, kwargs) {
        return fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: model,
                    method: method,
                    args: args,
                    kwargs: kwargs || {}
                }
            })
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.error) throw new Error(data.error.data.message || "RPC Error");
            return data.result;
        });
    }

    function getToDoActivityTypeId() {
        return rpcCall(
            "mail.activity.type", "search_read",
            [[["name", "ilike", "to"]]],
            { fields: ["id", "name"], limit: 5 }
        ).then(function (results) {
            if (results && results.length) {
                const exact = results.find(function (r) {
                    return r.name.toLowerCase().replace("-", "").includes("todo");
                });
                return exact ? exact.id : results[0].id;
            }
            return 1;
        });
    }

    function loadActivityUsers() {
        const select = document.getElementById("activity_user_id");
        if (!select) return;
        rpcCall(
            "res.users", "search_read",
            [[["share", "=", false], ["active", "=", true]]],
            { fields: ["id", "name"], order: "name asc", limit: 100 }
        ).then(function (users) {
            select.innerHTML = "";
            users.forEach(function (u) {
                const opt = document.createElement("option");
                opt.value = u.id;
                opt.textContent = u.name;
                select.appendChild(opt);
            });
            if (window.odoo && odoo.session_info && odoo.session_info.uid) {
                select.value = odoo.session_info.uid;
            }
        }).catch(function () {
            select.innerHTML = '<option value="">Error loading users</option>';
        });
    }

    function showActivityMsg(text, color) {
        const msgEl = document.getElementById("activity_msg");
        if (!msgEl) return;
        msgEl.textContent = text;
        msgEl.style.color = color;
        msgEl.style.display = "block";
    }

    function resetActivityForm() {
        const today = new Date().toISOString().split("T")[0];
        const dueDateEl = document.getElementById("activity_due_date");
        const summaryEl = document.getElementById("activity_summary");
        const noteEl    = document.getElementById("activity_note");
        const msgEl     = document.getElementById("activity_msg");
        if (dueDateEl) dueDateEl.value = today;
        if (summaryEl) summaryEl.value = "";
        if (noteEl)    noteEl.value    = "";
        if (msgEl)     msgEl.style.display = "none";
    }

    let usersLoaded = false;
    const activityViewBtn  = document.getElementById("activity_view");
    const activityPanel    = document.getElementById("activity_form_panel");

    if (activityViewBtn && activityPanel) {
        activityViewBtn.addEventListener("click", function () {
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
    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            if (activityPanel) activityPanel.style.display = "none";
        });
    }

    const submitBtn = document.getElementById("activity_submit_btn");
    if (submitBtn) {
        submitBtn.addEventListener("click", function () {
            const container = document.getElementById("main_3d_web");
            const resId     = container ? parseInt(container.dataset.resId) : null;
            const dueDate   = document.getElementById("activity_due_date")  ? document.getElementById("activity_due_date").value  : "";
            const summary   = document.getElementById("activity_summary")   ? document.getElementById("activity_summary").value   : "";
            const note      = document.getElementById("activity_note")      ? document.getElementById("activity_note").value      : "";
            const userId    = document.getElementById("activity_user_id")   ? parseInt(document.getElementById("activity_user_id").value) : false;

            if (!dueDate) {
                showActivityMsg("⚠️ Please set a due date.", "orange");
                return;
            }
            if (!resId) {
                showActivityMsg("⚠️ Could not determine document ID.", "orange");
                return;
            }

            getToDoActivityTypeId().then(function (activityTypeId) {
                return rpcCall(
                    "ir.model", "search_read",
                    [[["model", "=", "ir.attachment"]]],
                    { fields: ["id"], limit: 1 }
                ).then(function (models) {
                    if (!models || !models.length) throw new Error("ir.model not found for ir.attachment");
                    const resModelId = models[0].id;

                    return rpcCall("mail.activity", "create", [{
                        res_model_id:     resModelId,
                        res_id:           resId,
                        activity_type_id: activityTypeId,
                        date_deadline:    dueDate,
                        summary:          summary || "",
                        note:             note    || "",
                        user_id:          userId  || false
                    }]);
                });
            }).then(function () {
                showActivityMsg("✅ Activity scheduled!", "#00a09d");
                setTimeout(function () {
                    if (activityPanel) activityPanel.style.display = "none";
                    resetActivityForm();
                }, 1800);
            }).catch(function (err) {
                showActivityMsg("❌ " + err.message, "tomato");
                console.error("Activity create error:", err);
            });
        });
    }
});
