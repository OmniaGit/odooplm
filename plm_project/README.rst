PLM Project
===========

Link Odoo Projects to OdooPLM products and track project progress based on
the PLM lifecycle state of the associated components.

Overview
--------

Engineering projects often drive the creation and release of new product
revisions. This module connects the Odoo Project app with OdooPLM by allowing
project records to reference one or more products and by showing a progress
indicator computed from the PLM states of those products. Automated actions
can also move the project workflow forward as products reach key PLM states.

Key Features
------------

* Project form extended with a link to one or more PLM products
* Progress bar on the project computed from the engineering state of linked
  products (draft/confirmed/released ratio)
* Product form extended with a back-link showing which projects reference it
* Automated action support: trigger project stage transitions based on PLM
  state changes
* Activity integration: PLM activities on products are visible from the
  project context

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``project`` — Odoo Project
