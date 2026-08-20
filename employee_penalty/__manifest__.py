# -*- coding: utf-8 -*-
{
    'name': 'Employee Penalty',
    'version': '1.0',
    'summary': """ Employee Penalty Summary """,
    'author': 'AMT',
    'depends': ['base', 'hr', 'hr_payroll'],
    'data': [
        'data/payslip_input_type.xml',
        'security/ir.model.access.csv',
        'views/base_menu.xml',
        'views/penalty_type_views.xml',
        'views/employee_penalty_views.xml'
    ],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
