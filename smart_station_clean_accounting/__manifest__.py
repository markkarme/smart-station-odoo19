# -*- coding: utf-8 -*-
{
    'name': 'Smart Station Clean Accounting',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Customer receipts on Bank and Cash journals post as Paid',
    'description': """
Smart Station Clean Accounting
==============================

On install and upgrade, for every company:

* Ensure a Cash journal exists
* Point inbound payment methods of Bank and Cash journals at the journal
  liquidity account (asset_cash)

Customer invoices paid on those journals then become Paid immediately,
instead of staying In Payment until bank reconciliation.
    """,
    'author': 'Appivio',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'data/configure_journals.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
