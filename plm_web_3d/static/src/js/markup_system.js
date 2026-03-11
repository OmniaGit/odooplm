/** @odoo-module **/

let fabricCanvas = null;
let currentTool = null;
let startX, startY;
let tempShape = null;
let undoStack = [];
let redoStack = [];
let isRedoing = false;

window.addEventListener("load", () => {
    const markupBtn = document.getElementById("markup_button");
    if (markupBtn){
        markupBtn.addEventListener("click", openMarkupEditor);
    }
});

window.addEventListener("load", function () {
    const submitBtn = document.getElementById("submit_markup");
    if (submitBtn) {
        submitBtn.addEventListener("click", submitMarkup);
    }
});

function openMarkupEditor(){
    const editor = document.getElementById("markup_editor");
    if (!editor) return;
    editor.style.display = "block";
    if(!fabricCanvas){
        fabricCanvas = new fabric.Canvas("markup_canvas");
        resizeCanvas();
        initFabricEvents();
        initToolbar();
    }
}

function resizeCanvas(){
    const container = document.getElementById("main_3d_web");
    fabricCanvas.setWidth(container.clientWidth);
    fabricCanvas.setHeight(container.clientHeight);
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
        fabricCanvas.loadFromJSON(lastState, function() {
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
        fabricCanvas.loadFromJSON(nextState, function() {
            fabricCanvas.renderAll();
            isRedoing = false;
        });
    }
}

function initToolbar(){
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
        },
        "undo_btn": () => undo(),
        "redo_btn": () => redo(),
        "close_btn": () => {
            document.getElementById("markup_editor").style.display = "none";
        },
        "save_btn": saveMarkupWithBackground
    };

    for (const [id, func] of Object.entries(actions)) {
        const btn = document.getElementById(id);
        if (btn) btn.onclick = func;
    }
}

function initFabricEvents(){
    fabricCanvas.on("object:added", () => {
        if (!isRedoing) saveState();
    });

    fabricCanvas.on("object:modified", () => {
        saveState();
    });

    fabricCanvas.on("mouse:down", function(opt){
        if (opt.target) return;
        const pointer = fabricCanvas.getPointer(opt.e);
        startX = pointer.x;
        startY = pointer.y;
        if(tempShape) return;
        if(currentTool === "rect"){
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
        else if(currentTool === "circle"){
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
                fill: "#000"
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

    fabricCanvas.on("mouse:up", function(){
        if(tempShape){
            tempShape.set({
                selectable: true
            });
            fabricCanvas.setActiveObject(tempShape);
            tempShape.setCoords();
        }
        tempShape = null;
    });
}

function saveMarkupWithBackground(){
    const viewer = document.getElementById("main_3d_web");
    let fileName = viewer.dataset.fileName || "markup";
    const threeCanvas = document.getElementById("odoo_canvas");
    const bg = threeCanvas.toDataURL("image/jpg");
    fileName = fileName.replace(/\.[^/.]+$/, "") + ".jpg";
    const bgImg = new Image();
    bgImg.onload = function(){
        const tempCanvas = document.createElement("canvas");
        tempCanvas.width = threeCanvas.width;
        tempCanvas.height = threeCanvas.height;
        const ctx = tempCanvas.getContext("2d");
        ctx.drawImage(bgImg,0,0);
        const markupImg = new Image();
        markupImg.onload = function(){
            ctx.drawImage(markupImg,0,0);
            const final = tempCanvas.toDataURL("image/jpg");
            const link = document.createElement("a");
            link.href = final;
            link.download = fileName;
            link.click();
        };
        markupImg.src = fabricCanvas.toDataURL();
    };
    bgImg.src = bg;
}

function submitMarkup(){
    const comment = document.getElementById("markup_comment").value;
    const threeCanvas = document.getElementById("odoo_canvas");
    const bg = threeCanvas.toDataURL("image/jpg");
    const bgImg = new Image();
    bgImg.onload = function(){
        const tempCanvas = document.createElement("canvas");
        tempCanvas.width = threeCanvas.width;
        tempCanvas.height = threeCanvas.height;
        const ctx = tempCanvas.getContext("2d");
        ctx.drawImage(bgImg,0,0);
        const markupImg = new Image();
        markupImg.onload = function(){
            ctx.drawImage(markupImg,0,0);
            const finalImage = tempCanvas.toDataURL("image/jpg");
            sendMarkupToBackend(finalImage, comment);
        };
        markupImg.src = fabricCanvas.toDataURL({
            format: "jpg"
        });
    };
    bgImg.src = bg;
}

function sendMarkupToBackend(imageData, comment){
    const container = document.getElementById("main_3d_web");
    const resId = container.dataset.resId;
    const resModel = container.dataset.resModel;
    fetch("/plm_web_3d/save_markup", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {
                image: imageData,
                comment: comment,
                res_model: resModel,
                res_id: resId
            }
        })
    })
    .then(r => r.json())
    .then(data => {
        const commentTextarea = document.getElementById("markup_comment");
        if (commentTextarea) {
            commentTextarea.value = "";
        }
    });
}
