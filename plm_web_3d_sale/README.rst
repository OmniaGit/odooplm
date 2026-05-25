PLM Web 3D Sale
===============

Embed PLM 3D models as interactive WebGL previews in the Odoo e-commerce
product pages.

Overview
--------

This module bridges ``plm_web_3d`` and Odoo Website/eCommerce. It extends the
``product.image`` model so that a published 3D attachment (``ir.attachment``
with ``has_web3d = True`` and ``public = True``) can be linked to a product
image slot. The image slot then renders an ``<iframe>`` pointing to the 3D
viewer instead of a static image, giving website visitors an interactive 3D
preview of the product.

Key Features
------------

* Extends ``product.image`` with a link to a public 3D attachment
* Automatically sets the image preview thumbnail from the 3D model's stored
  preview or a default WebGL icon
* Renders an embedded ``<iframe>`` 3D viewer on the e-commerce product page
  when a 3D attachment is selected
* Supports ``.gltf``, ``.glb``, and ``.fbx`` formats for web display

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``website_sale`` — Odoo e-Commerce
