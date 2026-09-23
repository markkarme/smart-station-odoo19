# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Fill company_ids from existing company_id values."""
    departments = env["hr.department"].sudo().search([("company_id", "!=", False)])
    for department in departments:
        if department.company_id not in department.company_ids:
            department.write({"company_ids": [(4, department.company_id.id)]})
