Activity Validation
===================

Improve the communication process between Odoo PLM and CAD users by managing
modification requests, engineering orders, and BOM-linked activities.

Overview
--------

This module bridges the gap between the Odoo back-office and CAD users by
providing structured tools for managing change requests and engineering orders.
Activities can be assigned from Odoo directly to individual CAD users, who can
then acknowledge them from within their CAD application.

Key Features
------------

* Create and track modification requests from both Odoo and CAD applications
* Manage engineering change requests (ECR) and engineering orders (ECO)
* Assign and notify CAD users via Odoo activity system
* Control request status based on the associated BOM state
* Inspect which BOM lines are affected by a given modification

Dependencies
------------

* ``mail`` — Odoo Discuss / activity system
* ``plm`` — OdooPLM core module
