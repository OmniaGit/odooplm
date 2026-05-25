PLM Produce Only Latest
=======================

Restricts the product selector in Manufacturing orders to products that carry
an engineering code and are at their latest revision.

Overview
--------

Without this module, a production planner could accidentally schedule a
manufacturing order for an obsoleted revision of a component. Installing this
module filters the product domain in manufacturing orders so that only the
most recent (non-obsoleted) revision of each engineering part is selectable,
reducing the risk of producing outdated designs.

Key Features
------------

* Domain filter on the product field in Manufacturing order lines
* Only products with an ``engineering_code`` at the latest revision are shown
* Products without an engineering code (commercial/non-PLM items) remain
  unaffected

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``sale`` — Odoo Sales (required for domain infrastructure)
