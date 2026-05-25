PLM Sale Only Latest
====================

Restricts the product selector in Sale orders to products that are either
non-PLM items or at the latest revision of their engineering code.

Overview
--------

Quoting an obsoleted revision of a product to a customer leads to confusion and
potential quality issues. This module applies a domain filter on the product
field in sale order lines so that only products without an engineering code
(commercial items) or products at their latest revision are selectable.

Key Features
------------

* Domain filter on the product field in Sale order lines
* PLM-managed products (those with ``engineering_code``) are restricted to
  their latest revision
* Non-PLM products (no engineering code) remain fully selectable

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``sale_management`` — Odoo Sales Management
