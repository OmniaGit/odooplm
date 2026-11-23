PLM Purchase Share
==================

Let a vendor download from the portal the PDF of the drawings of what was
bought from them.

Overview
--------

A vendor needs the drawings of the parts on their purchase orders. This module
adds, on the purchase order page of the portal, a download button for each
line and one for the whole order.

What a vendor may get is decided by the portal scope of ``plm``
(``res.users._plm_portal_products`` and ``_plm_portal_document_policy``): the
products on their own order lines, when their partner, or their user, has a
PLM portal access other than *none*, and of those only the PDF printout of the
2D drawings, released, under modification or obsoleted since. The native CAD
file is never given.

Key Features
------------

* Portal route ``/my/plm/product/<product_id>/pdf``: the PDF of the drawings
  of one product; a product outside the user's scope answers 404
* Portal route ``/my/purchase/<order_id>/download_docs``: one PDF per ordered
  product, bundled into ``PO_<order_name>_Documents.zip``
* Both routes need a logged-in user (``auth='user'``); the order route also
  accepts the order's share ``access_token``
* The buttons show only where there is something to download

Usage
-----

Set **PLM Portal Access** to *View* on the vendor, give their contact a portal
user, and open the purchase order from the portal.

The backend report route (``/report/html/plm.product_production_pdf_latest/<id>``)
renders as the user, and a portal user can read neither products nor
attachments: do not link it from the portal.

Dependencies
------------

* ``plm`` — OdooPLM core module (portal scope and PDF composition)
* ``purchase`` — Odoo Purchase
* ``portal`` — Odoo Portal
* ``website`` — Odoo Website
