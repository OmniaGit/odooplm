PLM Cutted Parts
================

Extend Normal BOM creation for cut (raw-material) parts, with options to
explode or replace raw-material rows and a dedicated cut-parts report.

Overview
--------

Sheet metal, profiles, and other cut raw materials often require special
handling when promoting an Engineering BOM to a Normal BOM. This module adds
a wizard to the **Create Normal BOM** action that lets the user choose how
raw-material lines are treated, and adds a report listing all cut parts
related to a BOM.

Key Features
------------

* **None** — no change to the cut-part BOM line (default pass-through)
* **Explode** — adds an extra BOM level for the cut part, expanding its own
  BOM underneath the parent
* **Replace** — substitutes the cut-part product with its raw-material
  equivalent directly in the parent BOM
* Report: *Cut Parts* printout listing all cutted-part lines for a given BOM

Usage
-----

1. Navigate to **Engineering Parts**, select a product.
2. Open the action menu and choose **Create Normal BOM**.
3. In the wizard, select the desired action for each raw-material row.
4. Click **Create** to generate the Normal BOM.

Dependencies
------------

* ``mrp`` — Manufacturing BOMs
* ``plm`` — OdooPLM core module
* ``plm_automate_normal_bom`` — Normal BOM creation infrastructure
