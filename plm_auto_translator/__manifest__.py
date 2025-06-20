# -*- coding: utf-8 -*-
{
    "name": "PLM Auto Translator",
    "author": "OmniaSolutions",
    "version": "18.0.1.0.0",
    "summary": "PLM Auto Translator",
    "website": "https://odooplm.omniasolutions.website",
    "description": """Automatically update translation files for PLM modules""",
    "depends": [
        "plm",
    ],
    "data": [
        # security files
        "security/ir.model.access.csv",
        # data files
        "data/auto_translate_cron.xml",
        # views files
        "views/auto_translator_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
