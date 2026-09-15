PLM Automatic Engineering Code
==============================

Automatically generates part numbers (engineering codes) for PLM products
using configurable Odoo sequences.

Overview
--------

When a new product is created and its category is set, this module triggers
an automatic sequence to assign the ``engineering_code`` field (the Part Number).
Sequences can be configured globally or per product category, so different
product families can use different numbering series.

Key Features
------------

* Automatic part number generation via Odoo ``ir.sequence``
* Per-category sequence configuration on ``product.category``
* Onchange hook: changing the product category triggers a new code from the
  appropriate sequence
* Existing codes are preserved when the sequence has not changed

Configuration
-------------

Assign a sequence to one or more product categories via the
**Product Category** form (field: *Part Number sequence*). A global fallback
sequence with code ``plm.eng.code`` is used when no category-level sequence
is configured.

In a multi-company database the ``plm.eng.code`` sequence is global: every
company draws from the same counter, so part numbers stay unique across the
companies. To give a company its own series, duplicate the sequence, set the
company on the copy and change its prefix: Odoo uses the copy of the current
company in place of the global one. A sequence assigned to a product category
is used as it is, whatever company it belongs to.

Dependencies
------------

* ``product`` — Odoo product models
* ``plm`` — OdooPLM core module
