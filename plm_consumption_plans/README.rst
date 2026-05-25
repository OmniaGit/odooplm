PLM Consumption Plans
=====================

Manage reference and actual consumption plans for BOM lines, enabling
production planning based on historical or expected material usage over time.

Overview
--------

Consumption plans define how much of a material is expected (reference plan) or
actually consumed (actual plan) during a given time span. Plans are created from
templates and associated with products or product templates, then linked to BOM
lines so that planners can compare expected versus actual consumption at a
glance.

Key Features
------------

* **Consumption Plan Templates** — reusable plans with a name, time span
  (hours), and a consumption state
* **Consumption States** — configurable states for tracking plan progress
* Plans attachable to ``product.template`` and ``product.product`` records
* BOM line extension: each line can reference its associated consumption plan
* Wizard / action for bulk plan assignment

Dependencies
------------

* ``plm`` — OdooPLM core module
