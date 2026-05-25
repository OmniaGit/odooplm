PLM Client Custom Procedure
============================

Map custom CAD application properties to Odoo product and document fields,
enabling bidirectional synchronisation of non-standard metadata between CAD
clients and Odoo.

Overview
--------

CAD applications expose many custom properties (material, surface treatment,
drawing number, etc.) that are not part of the standard OdooPLM field set.
This module provides an ``odoo.cad.mapping`` configuration model where
administrators define which CAD property maps to which Odoo field on
``product.product`` or ``ir.attachment``. The CAD client reads this mapping
table and populates Odoo fields accordingly when uploading documents.

Key Features
------------

* ``odoo.cad.mapping`` model: configure pairs of (Odoo model + field,
  CAD property name)
* Unique constraint prevents duplicate field mappings per model
* Scoped to ``product.product`` and ``ir.attachment`` — the two primary PLM
  objects exchanged with CAD clients
* Per-user and per-group configuration for custom procedures
* Conversion stack line support for queued CAD conversion jobs

Configuration
-------------

Go to **PLM → Configuration → CAD Mappings** and create one record per
property you wish to synchronise. Set the Odoo model, the Odoo field, and the
corresponding CAD property name.

Dependencies
------------

* ``plm`` — OdooPLM core module
