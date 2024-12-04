# -*- encoding: utf-8 -*-

{
    'name': 'PLM Quality Base',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/Quality',
    'sequence': 50,
    'summary': 'Basic Feature for Quality',
    'depends': ['stock'],
    'description': """
        Quality Base
        ===============
        * Define quality points that will generate quality checks on pickings,
          manufacturing orders or work orders (quality_mrp)
        * Quality alerts can be created independently or related to quality checks
        * Possibility to add a measure to the quality check with a min/max tolerance
        * Define your stages for the quality alerts
    """,
    'data': [
        'security/quality.xml',
        'security/ir.model.access.csv',
        'data/mail_alias_data.xml',
        'data/quality_data.xml',
        'views/quality_views.xml',
    ],
    "license": "AGPL-3",
    'assets': {
        'web.assets_backend': [
            'plm_quality/static/src/**/*',
        ],
    }
}
