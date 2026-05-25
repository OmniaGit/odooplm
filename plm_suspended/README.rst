PLM Suspended State
===================

Adds a **Suspended** intermediate state to the PLM lifecycle workflow, between
*Released* and *Obsoleted*.

Overview
--------

The standard PLM state machine moves a product from *Released* directly to
*Obsoleted*. In some workflows an intermediate phase is needed — for example,
when a product is temporarily taken out of production but not yet fully retired.
This module inserts a *Suspended* state into the lifecycle, giving engineers
finer control over the transition to obsolescence.

State machine with this module installed::

    draft → confirmed → released ↔ undermodify → suspended → obsoleted

Key Features
------------

* New **Suspended** workflow state for products, documents, and BOMs
* State-aware write protection consistent with the other non-draft states
* Workflow buttons to move records into and out of the suspended state
* Compatible with all standard PLM lifecycle operations

Dependencies
------------

* ``mrp`` — Manufacturing BOMs
* ``plm`` — OdooPLM core module
