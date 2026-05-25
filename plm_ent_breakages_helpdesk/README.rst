PLM Breakages Helpdesk
======================

Enterprise extension that links PLM breakage records to Odoo Helpdesk tickets,
providing a complete traceability chain from customer complaint to production
root cause.

Overview
--------

This module extends ``plm_breakages`` by integrating breakage data with the
Odoo Helpdesk application. When a customer reports a component failure via a
helpdesk ticket, support agents can link the ticket directly to the relevant
breakage record, enabling engineering teams to prioritise investigations and
close the loop from field failure to BOM correction.

Key Features
------------

* Link helpdesk tickets to PLM breakage records
* Full breakage management (graphical view, BOM integration, manufacturing
  order indicators) inherited from ``plm_breakages``
* Provides traceability from customer complaint → helpdesk ticket → breakage
  analysis → BOM/MO correction

Dependencies
------------

* ``plm_breakages`` — core breakage management
* ``helpdesk`` — Odoo Helpdesk (Enterprise)
