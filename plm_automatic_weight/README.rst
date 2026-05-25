PLM Automatic Weight
====================

Computes product gross weight automatically from the Normal BOM structure,
CAD-imported weights, or a user-defined additional weight.

Overview
--------

Accurate weight data is essential for shipping, cost estimation, and compliance.
This module adds a **Compute BOM Weight** action that walks the Normal BOM tree,
accumulates component weights, and writes the result back to the product. Three
computation strategies are available, selectable per product.

Key Features
------------

* **Use Net Weight** — gross weight equals the product's net weight; only gross
  weight is used in production calculations.
* **Use CAD Weight** — CAD-imported weight plus any *Additional Weight* is
  written to *Gross Weight*.
* **Use Normal BOM** — the BOM-computed weight (*NBOM Weight Computed*) plus
  *Additional Weight* is written to *Gross Weight*.
* Bulk computation: select multiple products in the Engineering Parts list and
  run the action from the action menu.

Usage
-----

1. Navigate to **Engineering Parts** list view.
2. Select one or more products.
3. Open the action menu and choose **Compute BOM Weight**.
4. Review the updated *NBOM Weight Computed* and *Gross Weight* fields on each
   product form.

Dependencies
------------

* ``plm`` — OdooPLM core module
