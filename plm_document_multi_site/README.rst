PLM Document Synchronisation
=============================

Synchronise PLM CAD documents across multiple company sites or locations with
slow or intermittent network connections.

Overview
--------

Companies operating across multiple sites often need a local copy of CAD files
to avoid performance degradation over slow WAN links. This module adds a
document synchronisation layer to OdooPLM: each site runs a lightweight
OdooPLM file server that replicates the central Odoo document store.
Synchronisation can be triggered on demand for individual documents, on demand
for a batch, or automatically via a scheduled action.

.. note::
   A dedicated OdooPLM file server must be installed at each remote site.
   Contact OmniaSolutions (www.omniasolutions.website) for the server software.

Key Features
------------

* Local server configuration per site
* On-demand synchronisation of a single document from its form view
* Batch on-demand synchronisation from the document list
* Scheduled automatic synchronisation via Odoo cron
* Synchronisation history log with timestamps and status

Dependencies
------------

* ``plm`` — OdooPLM core module
