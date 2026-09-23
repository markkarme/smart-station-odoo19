# -*- coding: utf-8 -*-
{
    "name": "HR Department Multi Company",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "summary": "Allow one department to belong to multiple companies",
    "description": """
Allow assigning multiple companies on a department record.

Adds a Companies (many2many) field on hr.department and keeps company_id
as the primary company for compatibility with standard HR flows
(check_company, parent inheritance, etc.).
Departments become visible in every company they are assigned to.
    """,
    "author": "Smart Station",
    "license": "LGPL-3",
    "depends": ["hr"],
    "data": [
        "security/hr_department_security.xml",
        "views/hr_department_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
