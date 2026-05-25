PLM Web Revision
================

Create new product revisions entirely from the Odoo web interface, without
requiring a CAD client connection.

Overview
--------

In a standard OdooPLM workflow, revisions are initiated from a CAD editor.
This module adds the ability to start a revision directly from the Odoo browser
interface, making it possible for project managers or document controllers to
trigger revisions on products, their linked documents, Engineering BOMs, Normal
BOMs, and Spare BOMs in a single operation.

Key Features
------------

* Revision wizard accessible from the product form in Odoo web
* Revises the product and all related objects in one step:

  * Engineering documents (``ir.attachment``)
  * Engineering BOM (``plm_engineering``)
  * Normal BOM (``mrp.bom``)
  * Spare BOM (``plm_spare``)

* Increments the ``engineering_revision`` counter and resets the state to
  *draft*
* No CAD client or desktop software required

Dependencies
------------

* ``plm`` — OdooPLM core module
