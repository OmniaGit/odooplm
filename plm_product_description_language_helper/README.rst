PLM Product Description Language Helper
========================================

Automatically propagates product name and description changes to all installed
Odoo language translations when the PLM standard description is updated.

Overview
--------

OdooPLM uses a *standard description* field to compose the product name across
languages. When that field changes, this module automatically updates the
translated product name for every language installed in Odoo — eliminating the
need to manually open each language translation and retype the value.

Key Features
------------

* On save, changes to the standard description field trigger automatic
  propagation to all installed language translations
* Supports both simple string descriptions and the advanced multi-field
  description format
* Works with the PLM product name translation infrastructure
* Reduces manual effort in multilingual Odoo deployments

Usage
-----

1. Open a product form and edit the **Standard Description** field.
2. Save the product.
3. The product name translation for every installed language is updated
   automatically.

Dependencies
------------

* ``plm`` — OdooPLM core module
