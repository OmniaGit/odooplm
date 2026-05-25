PLM Automate Normal BOM
=======================

Automatically creates Normal BOMs for all released products that do not yet
have one, eliminating the need for manual BOM promotion after each release.

Overview
--------

In a typical PLM workflow a product moves through Engineering BOM → release →
Normal BOM. This module automates the last step: it scans all released products
and, for those missing a Normal BOM, generates one from their Engineering BOM.
The operation can be triggered on demand or scheduled via a server action.

Key Features
------------

* Bulk creation of Normal BOMs for released products in a single operation
* Scheduled action support for fully automated, periodic BOM promotion
* On-demand execution via the action menu in the Engineering Parts list
* Skips products that already have a Normal BOM to avoid duplicates

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``plm_engineering`` — Engineering BOM type
