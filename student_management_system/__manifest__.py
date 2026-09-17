# -*- coding: utf-8 -*-
{
    'name': "Student Management System",

    'summary': "Automates administrative tasks for educational institutions.Centralized data for easy access and management.Streamlined and efficient management of academic and financial processes",

    'description': """
Management of multiple branches, rooms, and schedules
Teacher and course assignments
Student course registration with auto-generated invoices
Financial integration for smooth operations
    """,

    'author': "Sun Group",
    'website': "https://www.sunacademy.com",

    'license': 'LGPL-3',
    'category': 'Services',
    'version': '19.0.1.0.0',

    'depends': ['base', 'mail', 'account'],

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ir_sequence_data.xml',
        'views/student_management_menu.xml',
        'views/student_management_branch_view.xml',
        'views/student_management_room_view.xml',
        'views/student_management_course_view.xml',
        'views/student_management_teacher_view.xml',
        'views/student_management_schedule_view.xml',
        'views/student_management_student_view.xml',
    ],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
