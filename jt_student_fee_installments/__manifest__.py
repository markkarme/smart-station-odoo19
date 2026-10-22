# -*- coding: utf-8 -*-
{
    'name': 'Student Fee Installments',
    'version': '19.0.1.1.18',
    'category': 'Education',
    'summary': 'Per-student fee plans with configurable basic/bus installments plus books and uniform',
    'description': """
Student Fee Installments
========================

* Fee plan linked to each student / academic year
* Configurable number of installments for:
  - أقساط المصاريف الدراسية
  - أقساط الباصات
* Other fees:
  - الكتب
  - اليونيفورم
* Track amount, receipt number and date per installment / fee
* Bus categories (name + price) assigned on student and fee plan

Depends only on jt_education_base (not jt_education_fees).
    """,
    'author': 'Appivio',
    'license': 'LGPL-3',
    'depends': ['jt_education_base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_fee_reminder.xml',
        'wizard/generate_fee_plans_wizard_views.xml',
        'views/bus_category_views.xml',
        'views/student_fee_payment_views.xml',
        'views/student_fee_plan_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
