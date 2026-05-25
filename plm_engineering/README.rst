PLM Engineering BOM
===================

Adds an **Engineering** BOM type and the tools to promote it to a Normal
manufacturing BOM once a product is released.

Overview
--------

In a PLM workflow the BOM received from a CAD application represents the
engineering intent and should be kept separate from the manufacturing BOM used
in production. This module introduces the *Engineering* BOM type so that all
CAD-uploaded BOMs are stored as Engineering BOMs. When a product is released,
the engineer can create the Normal BOM from it with a single click on the
product form.

Key Features
------------

* New BOM type: **Engineering** — assigned automatically to all BOMs uploaded
  by CAD clients
* Product form action to promote an Engineering BOM to a Normal (manufacturing)
  BOM
* Engineering BOMs remain intact after promotion for traceability
* Works in combination with ``plm_automate_normal_bom`` for bulk promotion

Dependencies
------------

* ``plm`` — OdooPLM core module
