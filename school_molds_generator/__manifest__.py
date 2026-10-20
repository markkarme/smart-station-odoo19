# -*- coding: utf-8 -*-
{
    'name': "School Molds Generator",
    'summary': "Fill school molds in an Excel-like view and download the sheet.",
    'category': 'Education',
    'version': '19.0.1.0.37',
    'author': 'Smart Station',
    'depends': ['jt_education_base', 'jt_education_exam'],
    'data': [
        'security/ir.model.access.csv',
        'security/school_mold_security.xml',
        'views/school_mold_views.xml',
        'views/student_mold_result_views.xml',
        'views/student_exam_views.xml',
        'views/health_insurance_letter_views.xml',
        'views/proof_registration_letter_views.xml',
        'views/health_insurance_enrollment_proof_views.xml',
        'views/health_insurance_response_views.xml',
        'report/health_insurance_letter_report.xml',
        'report/proof_registration_letter_report.xml',
        'report/health_insurance_enrollment_proof_report.xml',
        'report/health_insurance_response_report.xml',
        'report/mold_result_report.xml',
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
