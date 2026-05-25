PLM Report PDF Workorder — Enterprise
======================================

Enterprise extension of ``plm_pdf_workorder`` providing full shopfloor
integration between PLM 2D drawings and the Odoo ``mrp_workorder`` tablet
interface.

Overview
--------

Building on the community ``plm_pdf_workorder`` module, this Enterprise
extension hooks the PLM drawing viewer into the Odoo Manufacturing shopfloor
app (``mrp_workorder``). Operators using the tablet-based shopfloor UI can
view the product's 2D engineering drawing directly on their device without
switching applications.

Key Features
------------

* All features of ``plm_pdf_workorder`` (drawing viewer, worksheet toggle)
* Full integration with the Odoo Enterprise shopfloor / ``mrp_workorder``
  tablet interface
* PLM PDF document displayed within the shopfloor work order step

Dependencies
------------

* ``plm_pdf_workorder`` — community PDF workorder integration
* ``mrp_workorder`` — Odoo Enterprise shopfloor / work order app
