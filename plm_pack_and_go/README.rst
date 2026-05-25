PLM Pack and Go
===============

Download a ZIP archive containing all documents attached to a BOM structure,
with optional format conversion before export.

Overview
--------

When sharing a product BOM package with a supplier, subcontractor, or
manufacturing site, it is useful to collect all associated files (drawings,
3D models, PDFs, and other documents) into a single downloadable archive.
This module adds a **Pack and Go** wizard that explodes the BOM, gathers all
linked documents, optionally converts file formats, and produces a ZIP file
ready for download.

Key Features
------------

* Explodes the full BOM tree and collects documents from every level
* Documents are categorised into tabs: **2D**, **3D**, **PDF**, **Other**
* Per-line export type selection (e.g. export a 3D model as STL instead of
  the original format)
* **Force Types** button to apply a single export convention to all lines in a
  category at once
* **Clear** button to remove all documents of a given type from the export
* On-demand format conversion (via ``plm_automated_convertion``) before
  packaging
* Generates a downloadable ZIP that includes attachments plus a JSON metadata
  file with product info and document relationships
* Includes a checkout step to lock documents during export

Usage
-----

1. Navigate to **Engineering Parts**, select a product.
2. Open the action menu and choose **Pack and Go**.
3. Review and adjust the document lists per category.
4. Click **Create zip archive** to generate and download the ZIP.

Dependencies
------------

* ``plm`` — OdooPLM core module
