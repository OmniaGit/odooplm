PLM Purchase Share
==================

Generate and download a ZIP archive of product PDF datasheets for all lines
in a Purchase order, accessible from the supplier portal.

Overview
--------

Suppliers and internal buyers sometimes need a consolidated document package
for all products in a purchase order. This module exposes a portal route that
renders the PLM PDF datasheet for each ordered product and bundles them into a
single ZIP file available for immediate download.

Key Features
------------

* Portal route: ``/my/purchase/<order_id>/download_docs``
* Generates one PDF per ordered product using the PLM product report
* All PDFs are bundled into a ZIP named ``PO_<order_name>_Documents.zip``
* Accessible with ``auth='public'`` so the link can be shared with external
  users

Usage
-----

Navigate to the purchase order portal page and click the **Download Documents**
link, or share the URL
``/my/purchase/<order_id>/download_docs`` directly with the supplier.

Dependencies
------------

* ``plm`` — OdooPLM core module (provides the product PDF report)
* ``purchase`` — Odoo Purchase
* ``portal`` — Odoo Portal
* ``website`` — Odoo Website
