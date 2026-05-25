PLM BOM Summarize
=================

Automatically summarises duplicate BOM lines when a CAD client uploads a BOM,
consolidating repeated components into a single line with the summed quantity.

Overview
--------

CAD assemblies sometimes reference the same component multiple times across
different sub-assemblies, resulting in a flat BOM with duplicate part rows.
This module activates the ``SUMMARIZE_BOM`` context flag during the CAD client
``saveRelationNew`` call so that the BOM is automatically collapsed — multiple
lines for the same product are merged and their quantities summed — before the
BOM is stored in Odoo.

Key Features
------------

* Transparent summarisation: no user action required
* Activated automatically on every BOM save triggered by the CAD client
* Reduces BOM clutter and simplifies downstream manufacturing and purchasing

Dependencies
------------

* ``mrp`` — Manufacturing BOMs
* ``plm`` — OdooPLM core module
