# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2021 OmniaSolutions (<https://www.omniasolutions.website>).
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
    "name": "Product Lifecycle Management",
    "version": "19.0.1.0.1",
    "author": "OmniaSolutions",
    "website": "https://odooplm.omniasolutions.website",
    "category": "Manufacturing/Product Lifecycle Management (PLM)",
    "live_test_url": "https://www.v15.odooplm.cloud/",
    "sequence": 15,
    "license": "LGPL-3",
    "summary": "PLM-PDM Integration with main CAD editors (SolidWorks, SolidEdge, Inventor, Autocad, Thinkdesign, Freecad, Draftsight)",
    "images": ["static/img/odoo_plm.png"],
    "depends": ["base", "board", "product", "mrp"],
    "data": [
        "security/base_plm_security.xml",
        "report/product_report_document.xml",
        "report/bom_document.xml",
        "data/data.xml",
        "data/sequence.xml",
        "report/bom_structure_report_template.xml",
        "report/document_report_templates.xml",
        "report/product_report_templates.xml",
        "report/bom_structure.xml",
        "report/component_report.xml",
        "report/document_report.xml",
        "report/product_change_impact_template.xml",
        "report/attachment_change_impact_template.xml",
        "views/product_product_first.xml",
        "views/ir_attachment_view.xml",
        "views/ir_attachment_relations.xml",
        "views/plm_dbthread.xml",
        "views/mrp_extension.xml",
        "views/plm_backupdoc_view.xml",
        "views/plm_checkout_view.xml",
        "views/res_config_settings.xml",
        "views/plm_description_view.xml",
        "views/plm_finishing_view.xml",
        "views/plm_treatment_view.xml",
        "views/plm_material_view.xml",
        "views/product_product.xml",
        "views/product_template.xml",
        "views/ir_config_parameter.xml",
        "views/ir_cron.xml",
        "views/plm_cad_open.xml",
        "views/plm_cad_open_bck.xml",
        "views/mail_activity_type.xml",
        "views/menu.xml",
        "views/product_category.xml",
        "views/plm_temporaty.xml",
        "views/mrp_production.xml",
        # QwebTemplates
        "views/templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "plm/static/src/css/component_kanban.css",
            "plm/static/src/css/color_fields_tree.css",
            "plm/static/src/js/mrp_bom_overview_line.js",
            "plm/static/src/xml/mrp_bom_overview_table_inherit.xml",
            # many2one Widget
            # "plm/static/src/js/many2one_widget/many2one_widget.js",
            # "plm/static/src/js/many2one_widget/many2one_widget.xml",
        ],
        "web.report_assets_common": [
            "plm/static/src/scss/document_bom.scss",
            "plm/static/src/css/component_kanban.css",
            "plm/static/src/css/color_fields_tree.css",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
