# -*- coding: utf-8 -*-
{
    "name": "PLM Auto Translator",
    "author": "OmniaSolutions",
    "maintainer": "OmniaSolutions S.n.c di Boscolo Matteo & C",
    "version": "19.0.1.0.0",
    "images": ["static/description/cover.gif"],
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
    "external_dependencies": {
        "python": ["googletrans", "polib"],
        "apt": {
            "googletrans": "python3-pip",
            "polib": "python3-polib",
        },
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
