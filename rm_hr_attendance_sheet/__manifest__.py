# -*- coding: utf-8 -*-
{
    'name': "HR Attendance Sheet And Policies",

    'summary': """Managing  Attendance Sheets for Employees
        """,
    'description': """
        Employees Attendance Sheet Management   
    """,
    'author': "CUC",
    'website': "",
    'price': 99,
    'currency': 'USD',

    'category': 'Human Resources',
    'version': '19.0.1.0.1',
    'images': ['static/description/bannar.jpg'],

    'depends': [
        'base',
        'mail',
        'hr',
        'hr_payroll',
        'hr_holidays',
        'hr_attendance',
    ],
    'data': [
        'data/ir_sequence.xml',
        'data/data.xml',
        'data/ir_cron.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/change_att_data_view.xml',
        'views/hr_attendance_sheet_view.xml',
        'views/hr_attendance_policy_view.xml',
        'views/hr_contract_view.xml',
        'views/hr_public_holiday_view.xml',
        'views/attendance_sheet_batch_view.xml',
        'views/hr_payslip_view.xml'

    ],

    'license': 'OPL-1',
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
