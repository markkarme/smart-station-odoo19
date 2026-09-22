# -*- coding: utf-8 -*-
{
    "name": "HR Employee Multi Company",
    "version": "19.0.1.4.4",
    "category": "Human Resources",
    "summary": "Allow one employee to belong to multiple companies",
    "description": """
Allow assigning multiple companies on an employee record.

Adds a Companies (many2many) field on hr.employee and keeps company_id
as the primary company for compatibility with standard HR flows.
Employees become visible in every company they are assigned to.

Also syncs linked users, and allows reading employee resources while
working in any company the employee belongs to (needed for Attendances).
    """,
    "author": "Smart Station",
    "license": "LGPL-3",
    "depends": ["hr", "website", "resource"],
    "data": [
        "security/hr_employee_security.xml",
        "views/hr_employee_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
