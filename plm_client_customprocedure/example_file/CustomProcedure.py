# -*- encoding: utf-8 -*-

APPLICATION_SETTINGS = {
    'INTEGRATIONS': {
        'INVENTOR':{
            'KEY_NEW': 'Questa è una nuova chiave',
            'PRODUCT_PRODUCT':[{
                'CAD': 'NUMERO PARTE NEW',
                'CAD_READ_ONLY': False,
                'PLM': 'engineering_code',
                'PLM_READ_ONLY': False,
                'FUNCTION_CALL': False,
                'LANGUAGES': [{'LANGUAGE': '',
                               'CAD_REFERENCE': '',
                               'FUNCTION_CALL': False
                               }]
                },
                {
                'CAD': 'ENGINEERING MATERIAL',
                'CAD_READ_ONLY': False,
                'PLM': 'engineering_material',
                'PLM_READ_ONLY': False,
                'FUNCTION_CALL': False,
                'LANGUAGES': [{'LANGUAGE': '',
                               'CAD_REFERENCE': '',
                               'FUNCTION_CALL': False
                               }]
                },            
                ],
            
            'PLM_DOCUMENT':[{
                'CAD': 'DOCNAME NEW',
                'CAD_READ_ONLY': False,
                'PLM': 'name',
                'PLM_READ_ONLY': False,
                'FUNCTION_CALL': False,
                'LANGUAGES': [{'LANGUAGE': '',
                               'CAD_REFERENCE': '',
                               'FUNCTION_CALL': False
                               }]
                },           
                ],
            }
        },
    'OPTIONS_GROUPING': {
        'GRUPPO_1': {
            'NAME': 'Name Group one UNO',
            'ITEMS':[
                {'KEY': 'AUTOMATIC_SAVE',
                 'TYPE': 'checkbox',
                 'DEFAULT': False,
                 'NAME': 'Automatic save changes in the CAD after saving procedure.',
                 'WEB_HELP_URL': '',
                 'TOOLTIP': '''
        Nuovo Tooltip
        If checked: After Save procedure the software try to save changes in the CAD automatically.
        If not cheked: After Save procedure the software leaves unsaved changes in the CAD, you hae to save manually before to continue.
        DEFAULT: Checked''',
                }],
            },
        },
    }