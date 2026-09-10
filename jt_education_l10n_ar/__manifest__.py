# -*- coding: utf-8 -*-
{
    'name': "Education Arabic Translations",
    'summary': "Install on production to apply Arabic translations for the education modules without upgrading each one.",
    'description': """
Arabic translation pack for the upgraded education modules.

Install this module on production after copying it to the addons path.
It overwrites existing Arabic terms (menus, views, field labels) for:

* jt_education_base, reports, health, exam, event, timetable, fees,
  library, hostel, assignment, attendance
* jt_counseling
* jt_education_portal, jt_portal_student
* student_management, student_management_system

Arabic must already be loaded, or this module will activate the official
Odoo Arabic language (ar_001). Upgrade this module later to refresh terms.
    """,
    'category': 'Localization',
    'version': '19.0.1.0.0',
    'author': 'Smart Station',
    'depends': ['jt_education_base'],
    'data': [],
    'post_init_hook': 'post_init_hook',
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
