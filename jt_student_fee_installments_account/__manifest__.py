# -*- coding: utf-8 -*-
{
    'name': 'Student Fee Installments Accounting',
    'version': '19.0.1.0.2',
    'category': 'Education/Accounting',
    'summary': 'Create customer invoices and payments from student fee installments',
    'description': """
Student Fee Installments — Accounting
=====================================

Bridge between student fee installments and Odoo Accounting:

* Configure income products per fee category (basic, bus, books, uniform)
* Create a customer invoice per installment / other fee line
* Register payment → journal entries via standard Odoo flow
* Sync paid amount, date and receipt back onto the fee line
    """,
    'author': 'Appivio',
    'license': 'LGPL-3',
    'depends': [
        'jt_student_fee_installments',
        'account',
        'product',
    ],
    'data': [
        'data/product_data.xml',
        'views/res_config_settings_views.xml',
        'views/student_fee_installment_views.xml',
        'views/student_fee_plan_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
