# -*- coding: utf-8 -*-
{
    'name': 'مخالفات الطلاب',
    'version': '19.0.1.4.1',
    'summary': 'تتبع مخالفات الطلاب ودراسات الحالة والإجراءات التأديبية',
    'category': 'Education',
    'depends': ['jt_education_base'],
    'data': [
        'security/ir.model.access.csv',
        'security/student_violation_security.xml',
        'views/student_violation_views.xml',
        'views/case_study_views.xml',
        'views/student_views.xml',
        # Menus last: parent + child menus need actions defined above
        'views/action_and_menu.xml',
        'report/case_study_report.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
