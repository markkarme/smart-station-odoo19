# -*- coding: utf-8 -*-
{
    'name': 'Cancel Stock Moves',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Cancel stock moves and reset them to draft from Moves Analysis',
    'description': """
Cancel Stock Moves
==================

Cancel multiple stock moves and optionally reset them to draft from
Inventory → Reporting → Moves Analysis.

* **Cancel** — cancel selected moves (done moves are reversed first)
* **Cancel & Reset Draft** — cancel/reverse then set moves back to draft
    """,
    'author': 'INKERP',
    'website': 'https://www.inkerp.com',
    'depends': ['stock'],
    'data': [
        'views/stock_move_view.xml',
    ],
    'images': ['static/description/banner.gif'],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
