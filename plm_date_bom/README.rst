PLM Date BOM
============

View and update Normal BOMs that contain obsoleted components, replacing them
with the latest released revision of each component.

Overview
--------

Over time components in a Normal BOM can become obsoleted as new revisions are
released. This module highlights BOMs containing obsoleted lines (shown in red
in the tree view) and provides a wizard to update or clone them using the
latest released component revisions.

Key Features
------------

* BOM tree view filter: quickly isolate BOMs with obsoleted components
* Visual indicator (red row) for BOMs containing obsoleted lines
* **Update BOM** button: replace all obsoleted BOM lines with the latest
  released revision in place
* **All Related BOMs to Update**: open a tree showing all child BOMs that also
  contain obsoleted components
* Wizard with two update strategies:

  * *Replace obsoleted lines* — updates lines directly in the current BOM
  * *Clone and update* — creates a new BOM revision with updated components
    and deactivates the old one

Dependencies
------------

* ``plm`` — OdooPLM core module
* ``plm_web_revision`` — revision infrastructure
