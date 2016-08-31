# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution    
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Product Lifecycle Management',
    'version': '1.1',
    'author': 'OmniaSolutions',
    'website': 'http://www.omniasolutions.eu',
    'category': 'Product Lifecycle Management',
    'sequence': 15,
    'summary': 'PLM Integration with main CAD editors',
    'images': ['images/odooplmjpg.JPG',
               'images/odooPLMV9_2.PNG',
               'images/EngineeringPart.jpeg',
               'images/OpenComponent.jpeg',
               'images/OpenDocument.jpeg'],
    'depends': ['base',
                'board',
                'document',
                'product',
                'mrp'],
    'description': """
Manage Product Lifecycle Management in OpenERP
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


Supported Editors :
-------------------

    * Category : CAD / Mechanical CAD

        * ThinkDesign 2009.3 (and above)
        * SolidWorks 2011 (and above)
        * Inventor 2011 (and above)
        * SolidEdge ST3 (and above)

    * Category : CAE / Electrical CAD
        * SPAC 2013 (needs SDProget connector license)
    """,
    'data': [
            'security/base_plm_security.xml',
            'views/import_stylesheet.xml',
            'views/mrp_extension.xml',
            'views/plm_backupdoc_view.xml',
            'views/plm_checkout_view.xml',
            'views/plm_config_settings.xml',
            'views/plm_description_view.xml',
            'views/plm_document_relations.xml',
            'views/plm_document_view.xml',
            'views/plm_dashboard_view.xml',     # After plm_document_view.xml
            'views/plm_finishing_view.xml',
            'views/plm_material_view.xml',
            'views/product_product_extension_view.xml',
            'views/product_template.xml',
            'views/sequence.xml',
            'views/menu.xml',

            'views/workflow/plm_document_workflow.xml',
            'views/workflow/product_product_workflow.xml',

            'report/bom_structure_report.xml',
            'report/bom_structure.xml',
            'report/checkout_report.xml',
            'report/component_report.xml',
            'report/document_report.xml',
            'views/product_product_kanban.xml',  # After component_report.xml
            # security
            'security/res.groups.csv',
            # TODO: reenable'security/ir.model.access.csv',
            ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
