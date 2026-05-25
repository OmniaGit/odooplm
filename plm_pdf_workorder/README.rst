PLM Report PDF Workorder
========================

Display PLM 2D drawings directly inside manufacturing work orders, allowing
operators to switch between the routing worksheet and the product drawing
without leaving the shopfloor interface.

Overview
--------

Operators on the shopfloor often need to consult the engineering drawing while
processing a work order. This module embeds the PLM 2D PDF document into the
work order form so that it can be viewed alongside — or instead of — the
routing worksheet. The routing tab also gains a toggle to enable or disable
the use of the worksheet per routing step.

.. note::
   Full shopfloor integration (``mrp_workorder``) requires the Enterprise
   extension ``plm_pdf_workorder_enterprise``.

Key Features
------------

* 2D drawing viewer embedded in the work order form
* Toggle switch: show routing worksheet or PLM drawing per work order
* Routing tab: enable/disable worksheet use per routing step
* Works with the PDF documents managed by the PLM module

Dependencies
------------

* ``plm`` — OdooPLM core module
