# -*- encoding: utf-8 -*-
{
    "name": "PLM MRP Work Order",
    "version": "18.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "sequence": 51,
    "summary": """Work Orders, Planning, Stock Reports.""",
    "depends": [
        "plm_quality",
        "mrp",
        "barcodes",
        "plm_web_gantt",
        "web_tour",
        "hr_hourly_cost",
    ],
    # "auto_install": ["mrp"],
    "description": """extension for MRP
* Work order planning.  Check planning by Gantt views grouped by production order / work center
* Traceability report
* Cost Structure report""",
    "data": [
        "security/ir.model.access.csv",
        "security/mrp_workorder_security.xml",
        "data/mrp_workorder_data.xml",
        "views/hr_employee_views.xml",
        "views/quality_views.xml",
        "views/mrp_bom_views.xml",
        "views/mrp_workorder_views.xml",
        "views/mrp_operation_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_workcenter_views.xml",
        "views/stock_picking_type_views.xml",
        "views/res_config_settings_view.xml",
        "views/mrp_workorder_views_menus.xml",
        "wizard/additional_workorder_views.xml",
        "wizard/propose_change_views.xml",
    ],
    "demo": [
        "data/mrp_production_demo.xml",
        "data/mrp_workorder_demo.xml",
        "data/mrp_workorder_demo_stool.xml",
    ],
    "license": "AGPL-3",
    "assets": {
        "web.assets_backend": [
            "plm_mrp_workorder/static/src/**/*.scss",
            "plm_mrp_workorder/static/src/**/*.js",
            "plm_mrp_workorder/static/src/**/*.xml",
            ("remove", "plm_mrp_workorder/static/src/mrp_workorder_gantt_*"),
        ],
        "web.assets_backend_lazy": [
            "plm_mrp_workorder/static/src/mrp_workorder_gantt_*",
        ],
    },
}
