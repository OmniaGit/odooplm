PLM Compare BOM
===============

Compare two Bills of Materials side by side to identify added, removed, and
changed components.

Overview
--------

During engineering change management it is essential to understand exactly what
has changed between two BOM revisions. This module adds a wizard-based
comparison tool that takes two BOM records as input and produces a structured
diff showing which lines are present in one BOM but not the other, and where
quantities or other fields differ.

Key Features
------------

* Select any two BOMs to compare regardless of product or revision
* Structured diff output: added lines, removed lines, and changed quantities
* Accessible from the Engineering Parts action menu

Dependencies
------------

* ``plm`` — OdooPLM core module
