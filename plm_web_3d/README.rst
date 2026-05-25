PLM Web 3D Viewer
=================

Interactive browser-based 3D and 2D CAD viewer embedded directly in Odoo PLM,
built on Three.js. No desktop software or CAD licence required for reviewers.

Overview
--------

This module embeds a full-featured WebGL viewer inside the PLM document form.
Engineers and reviewers can inspect 3D assemblies and 2D drawings, measure
distances, mark up screenshots, and create Odoo activities — all without
leaving the browser.

Supported File Formats
----------------------

**3D formats**

* ``.glb`` / ``.gltf`` — GL Transmission Format (recommended for assemblies)
* ``.3mf`` — 3D Manufacturing Format with named components
* ``.stl`` — Stereolithography mesh
* ``.fbx`` — Autodesk FBX
* ``.obj`` — Wavefront OBJ
* ``.wrl`` — VRML
* ``.stp`` / ``.step`` — auto-converted to 3MF on first open (requires
  ``plm_automated_convertion``)
* ``.json`` — Three.js JSON scene

**2D formats**

* ``.dxf`` — 2D drawing (rotation disabled, 3D controls hidden)
* ``.svg`` — Scalable Vector Graphics

Key Features
------------

* WebGL 3D viewer with orbit, pan, zoom, and section-plane controls
* Assembly explosion view and part-level transparency control
* Measurement tool: click two snap points to display the distance in mm
* Part hover tooltip showing the component name fetched from Odoo
* Markup / annotation tools (via Fabric.js): draw on screenshots, add
  comments, create Odoo activities
* Section cap rendering and configurable background colour
* Square preview image capture and save directly to the document record
* DXF 2D drawing viewer with panning and zooming
* Toolbar with colour picker, visibility toggles, and zoom-to-window

Installation
------------

Three.js and the DXF viewer are included as git submodules under
``static/src/js/lib/``. Run ``git submodule update --init`` after cloning.

Dependencies
------------

* ``plm`` — OdooPLM core module
