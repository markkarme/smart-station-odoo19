# -*- coding: utf-8 -*-
{
    'name': "School Molds Generator",
    'summary': "Fill school molds in an Excel-like view and download the sheet.",
    'category': 'Education',
    'version': '19.0.1.0.3',
    'author': 'Smart Station',
    'depends': ['jt_education_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/school_mold_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'school_molds_generator/static/src/mold_grid/mold_grid_field.js',
            'school_molds_generator/static/src/mold_grid/mold_grid_field.xml',
            'school_molds_generator/static/src/mold_grid/mold_grid_field.scss',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
