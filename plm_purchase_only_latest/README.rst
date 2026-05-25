PLM Purchase Only Latest
========================

Restricts the product selector in Purchase orders to products that are either
non-PLM items or at the latest revision of their engineering code.

Overview
--------

Purchasing an obsoleted revision of a component wastes time and money. This
module applies a domain filter on the product field in purchase order lines so
that only products without an engineering code (commercial items) or products
at their latest revision are selectable.

Key Features
------------

* Domain filter on the product field in Purchase order lines
* PLM-managed products (those with ``engineering_code``) are restricted to
  their latest revision
* Non-PLM products (no engineering code) remain fully selectable

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``purchase`` — Odoo Purchase
