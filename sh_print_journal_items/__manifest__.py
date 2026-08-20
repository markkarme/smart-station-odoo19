# -*- coding: utf-8 -*-
{
    "name": "Print Journal Items",

    "author": "Softhealer Technologies",

    "license": "OPL-1",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "version": "19.0.1.0.0",

    "category": "Accounting",

    "summary": "print journal items app print multiple items module print journal items print journals journal items report print journal report journal item report odoo",

    "description": """This module useful to print journal items.""",

    "depends": ["account"],

    "external_dependencies": {
        "python": ["xlwt"],
    },

    "data": [
            "security/ir.model.access.csv",
            "report/account_move_line_templates.xml",
            "views/journal_item_xls_report_views.xml",
        ],
    "images": ["static/description/background.png", ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": 7,
    "currency": "EUR"

}
