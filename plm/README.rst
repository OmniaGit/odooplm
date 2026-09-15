Manage Product Lifecycle Management in Odoo
==============================================

This application enables a group of people to intelligently and efficiently manage 3D Models and 2D Drawings, directly from CAD editors.

It manages fundamental revisions of Products and Documents, helps to work in Concurrent Engineering with access policies to documents.

Moreover, it adds many reports and views on Bill of Materials or related to them. It helps to share 2D documents using PDF embedded.

New functionality Compare BoMs helps to understand differences between Bill of Materials.

Key Features :
--------------

    * Editor Integration
    * Document Management
    * Document Relationship
    * Engineering Bill of Materials
    * Spare Parts BoM & Reports
    * Compare BoMs


Multi-company :
---------------

    All the PLM sequences (document codes, database threads, materials,
    finishings, treatments, descriptions) are global: every company draws from
    the same counter, so codes stay unique across the companies.

    A company that needs its own numbering must be given it explicitly: in
    *Settings > Technical > Sequences & Identifiers > Sequences*, duplicate
    the PLM sequence, set the company on the copy and change its prefix, so
    that its codes cannot clash with the ones of the other companies. Odoo uses
    the copy of the current company in place of the global sequence.


Supported Editors :
-------------------

    * Category : CAD / Mechanical CAD

        * ThinkDesign 2009.3 (and above)
        * SolidWorks 2011 (and above)
        * Inventor 2011 (and above)
        * SolidEdge ST3 (and above)
        * Autocad 2013 (and above)
        * FreeCAD 0.16 (and above)

    * Category : CAE / Electrical CAD
        * SPAC 2013 (needs SDProget connector license)
