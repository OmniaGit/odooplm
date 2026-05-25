PLM Auto Internal Reference
===========================

Automatically populates the product's **Internal Reference** (``default_code``)
field from its PLM engineering code and revision number.

Overview
--------

In an OdooPLM environment each product is identified by an ``engineering_code``
and an ``engineering_revision``. This module keeps the standard Odoo
``default_code`` field in sync with those two values, producing a reference in
the format::

    <engineering_code>_<engineering_revision>

This avoids manual data entry and ensures consistency between PLM identifiers
and the internal reference used across purchasing, sales, and inventory.

Key Features
------------

* Automatic computation of ``default_code`` from ``engineering_code`` and
  ``engineering_revision``
* Zero configuration — works immediately after installation

Dependencies
------------

* ``plm`` — OdooPLM core module
