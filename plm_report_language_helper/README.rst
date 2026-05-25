PLM Report Language Helper
==========================

Generate spare-BOM or BOM reports in multiple languages simultaneously using
a simple wizard interface.

Overview
--------

In international manufacturing environments, BOM and spare-parts reports often
need to be issued in the language of the customer, supplier, or manufacturing
site. This module adds a wizard accessible from the Engineering Parts action
menu that lets users select one or more output languages and generate the
corresponding reports in a single operation.

Key Features
------------

* Wizard to select report type (spare BOM or standard BOM report) and target
  language(s)
* Single-click generation of multi-language PDF reports
* Downloadable output directly from the wizard
* Accessible via the action menu on Engineering Parts

Usage
-----

1. Navigate to **Engineering Parts**, select a product.
2. Open the action menu and choose **Create report spare BOM** or
   **Create BOMs report**.
3. Select the desired output languages in the wizard.
4. Click **Create** and download the generated PDFs.

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``plm_spare`` — Spare BOM management
