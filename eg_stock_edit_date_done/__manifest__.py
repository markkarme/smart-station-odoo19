# -*- coding: utf-8 -*-
{
    'name': 'Stock Picking Edit Done Date',
    'version': '19.0.1.0.1',
    'category': 'Inventory/Inventory',
    'summary': 'Edit the effective (done) date on validated stock pickings',
    'description': """
Stock Picking Edit Done Date
============================

Allows authorized users to update the effective date (date_done) on done or
cancelled transfers via a wizard on the picking form.

* Security group: **Update Effective Date**
* Button on the transfer form opens a wizard to set the new date
* Writing date_done also updates related stock move / move line dates (core behavior)
    """,
    'author': 'INKERP',
    'website': 'https://www.inkerp.com',
    'depends': ['stock'],
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_view.xml',
        'wizards/update_effective_date_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
