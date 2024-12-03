# -*- coding: utf-8 -*-
{
    "name": "PLM Web Gantt",
    "category": "Hidden",
    "description": """
        Web Gantt chart view.
        =============================
    """,
    "version": "18.0.1.0.0",
    "depends": ["web"],
    "assets": {
        "web._assets_primary_variables": [
            "plm_web_gantt/static/src/gantt_view.variables.scss",
        ],
        "web.assets_backend_lazy": [
            "plm_web_gantt/static/src/**/*",
            ("remove", "plm_web_gantt/static/src/**/*.dark.scss"),
        ],
        "web.assets_backend_lazy_dark": [
            "plm_web_gantt/static/src/**/*.dark.scss",
        ],
        "web.dark_mode_variables": [
            (
                "before",
                "web_enterprise/static/src/**/*.variables.scss",
                "plm_web_gantt/static/src/**/*.variables.dark.scss",
            ),
        ],
    },
    "auto_install": False,
    "license": "AGPL-3",
}
