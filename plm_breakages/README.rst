PLM Breakages
=============

Manage and track component breakages across products, BOMs, and manufacturing
orders.

Overview
--------

When a component breaks during production it is important to record the event,
analyse recurring breakage patterns, and link the information back to the BOM
and manufacturing order. This module adds a dedicated **Breakages** menu with
graphical views, and embeds breakage indicators directly on BOM lines and
manufacturing orders.

Key Features
------------

* Dedicated **Breakage** menu with a graphical (kanban/graph) overview of
  breakage records
* Create breakage records linked to a specific product
* BOM form: smart button showing how many BOM lines have associated breakages
* Manufacturing order form: indicator button showing whether any ordered
  components have breakage history
* Full form view for entering breakage details (date, quantity, cause, notes)

Dependencies
------------

* ``base``
* ``product`` — Odoo product models
* ``mrp`` — Manufacturing orders and BOMs
* ``plm`` — OdooPLM core module
