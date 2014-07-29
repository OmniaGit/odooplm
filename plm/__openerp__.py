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
    'images': ['images/EngineeringPart.jpeg','images/OpenComponent.jpeg','images/OpenDocument.jpeg'],
    'depends': ['base','board','document','product','mrp'],
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
        'install/board_plm_view.xml',
        'security/base_plm_security.xml',
        'security/res.groups.csv',
        'security/ir.model.access.csv',
        'install/res_config_view.xml',
        'install/plmdocuments/document_view.xml',
        'install/plmdocuments/document_workflow.xml',
        'install/plmdocuments/backupdoc_view.xml',
        'install/plmdocrelations/document_relations.xml',
        'install/plmcomponents/component_view.xml',
        'install/plmcomponents/component_workflow.xml',
        'install/plmdescriptions/description_view.xml',
        'install/plmdescriptions/description_sequence.xml',
        'install/plmsparebom/sparebom_view.xml',
        'install/plmsparebom/description_view.xml',
        'install/plmcomponentrelations/relations_view.xml',
        'install/plmcomparebom/compare_bom_view.xml',
        'install/plmcheckedout/checkout_view.xml',
        'install/report/bom_structure.xml',
        'install/report/component_report.xml',
        'install/report/document_report.xml',
        'install/report/checkout_report.xml',
        'install/plmmaterials/material_sequence.xml',
        'install/plmmaterials/material_view.xml',
        'install/plmfinishings/finishing_sequence.xml',
        'install/plmfinishings/finishing_view.xml',
       ],
    'demo': [
        ],
    'test': [
        ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
