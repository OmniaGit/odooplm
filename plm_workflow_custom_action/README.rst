PLM Workflow Custom Actions
===========================

Configure Odoo automated actions that trigger on PLM workflow state
transitions, enabling custom business logic without code changes.

Overview
--------

Odoo's ``base_automation`` module allows server actions to fire on record
changes. This module integrates that infrastructure with the PLM state machine
so that administrators can define actions that execute automatically when a
product, document, or BOM moves between PLM states (e.g., send a notification
when a product is released, or create a task when it enters *Under Modification*).

Key Features
------------

* Use the standard Odoo Automated Actions configuration to define PLM triggers
* Trigger actions on any PLM state transition
  (draft, confirmed, released, undermodify, obsoleted)
* No Python code required — actions are configured entirely from the UI
* Supports all Odoo server action types: email, webhook, Python code, record
  update, etc.

Configuration
-------------

Go to **Settings → Technical → Automation → Automated Actions** and create a
new action targeting the PLM model of interest (``product.template``,
``ir.attachment``, or ``mrp.bom``). Filter on the ``engineering_state`` field
to trigger on the desired transition.

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``base_automation`` — Odoo Automated Actions
