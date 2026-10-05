# -*- coding: utf-8 -*-
{
    'name': 'Student Fee Exceptions & Penalties',
    'version': '19.0.1.0.0',
    'category': 'Education',
    'summary': 'Late payment weekly penalties and fee exceptions (more installments / discount)',
    'description': """
Student Fee Installments — Exceptions & Penalties
=================================================

* Due date (تاريخ الاستحقاق) on each installment
* Late penalty = weeks after due date × price per week (default 50)
* Total late penalties on the fee plan and per line
* Exception wizard:
  - Increase number of installments (basic or bus) + document
  - Discount on unpaid lines (fixed or %) + document
    """,
    'author': 'Appivio',
    'license': 'LGPL-3',
    'depends': ['jt_student_fee_installments'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/student_fee_exception_views.xml',
        'wizard/fee_exception_wizard_views.xml',
        'views/student_fee_plan_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
