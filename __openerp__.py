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
    'version': '1.0',
    'category': 'LifeCycle Management',
    'depends': ['base', 'process','document','product','mrp'],
    'author': 'OmniaSolutions',
    'description': """ This is a Product Lifecycle Management system providing:
    
    * Editor Integration
    * Document Management
    * Document Indexation
    * Documents Relationship
    * Engineering Bill of Materials
    * Spare Part Bom & Report
    
    
    Supported Editors :
    
    - Category : CAD / Mechanical CAD
    * ThinkDesign 2009.3 (and above)
    * SolidWorks 2011.1 (and above)
    """,
    'website': 'http://www.omniasolutions.eu',
    'images': ['images/EngineeringPart.jpeg','images/OpenComponent.jpeg','images/OpenDocument.jpeg'],
    'init_xml': [
        ],
    'update_xml': [
        'install/plmviews/plm_menu.xml',
        'install/plmdocuments/document_view.xml',
        'install/plmdocuments/document_workflow.xml',
        'install/plmdocuments/backupdoc_view.xml',
        'install/plmcomponents/component_view.xml',
        'install/plmcomponents/component_workflow.xml',
        'install/plmdescriptions/description_sequence.xml',
        'install/plmsparebom/sparebom_view.xml',
        'install/plmsparebom/description_view.xml',
        'install/plmcomponentrelations/relations_view.xml',
        'install/plmcheckedout/checkout_view.xml',
        'install/report/bom_structure.xml',
        'install/report/component_report.xml',
        'install/report/document_report.xml',
        'install/report/checkout_report.xml',
        'install/plmmaterials/material_sequence.xml',
        'install/plmmaterials/material_view.xml',
        'install/plmfinishings/finishing_sequence.xml',
        'install/plmfinishings/finishing_view.xml',
        'security/base_plm_security.xml',
        'security/ir.model.access.csv',
        'security/ir.actions.act_window.csv',
        'security/res.groups.csv',
        'plm_installer.xml',
        ],
    'demo_xml': [
        ],
    'installable': True,
    'active': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
