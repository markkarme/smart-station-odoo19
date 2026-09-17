# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Fill company_ids and sync linked portal/internal users."""
    employees = env["hr.employee"].sudo().search([("company_id", "!=", False)])
    for employee in employees:
        if employee.company_id not in employee.company_ids:
            employee.write({"company_ids": [(4, employee.company_id.id)]})
        else:
            employee._sync_linked_user_companies()
