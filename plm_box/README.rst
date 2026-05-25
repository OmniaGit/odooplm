PLM Box
=======

A versioned, hierarchical container for PLM documents and sub-boxes, modelled
after the core PLM revision lifecycle.

Overview
--------

``plm.box`` inherits from ``revision.plm.mixin``, giving each box the same
engineering code, revision number, and lifecycle state machine used by PLM
products and documents. Boxes can be nested (parent/child via ``_parent_store``)
and can aggregate ``ir.attachment`` documents. A CSV structure field allows
describing the expected content schema of a box.

This module also integrates with ``account``, ``project``, and ``sale`` to link
boxes to accounting, project, and sales workflows.

Key Features
------------

* Full PLM revision lifecycle (draft → confirmed → released → obsoleted) on box
  records
* Hierarchical box tree with ``_parent_store`` for efficient querying
* Many-to-many relationship between boxes (parent/child boxes)
* Document attachments via ``ir.attachment`` one-to-many relation
* CSV structure definition for expected box content
* Extends ``plm.checkout`` and ``ir.attachment`` for box-aware document checkout

Dependencies
------------

* ``base``
* ``plm`` — OdooPLM core module
* ``account``
* ``project``
* ``sale``
