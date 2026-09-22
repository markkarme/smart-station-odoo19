# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Align resource multi-company access with multi-company employees.

    Opening an attendance in company2 loads the employee resource, which often
    still has company_id = main company. Allow access when:
    - resource company is active, or
    - linked employee belongs to an active company, or
    - current user is the employee / their manager (same as hr.employee rule).
    """
    cr.execute(
        """
        UPDATE ir_rule
           SET name = %s,
               domain_force = %s
         WHERE id = (
            SELECT res_id
              FROM ir_model_data
             WHERE module = 'resource'
               AND name = 'resource_resource_multi_company'
               AND model = 'ir.rule'
         )
        """,
        (
            "resource.resource multi-company (employee companies)",
            "["
            "'|', '|', '|', '|', "
            "('company_id', 'in', company_ids + [False]), "
            "('employee_company_ids', 'in', company_ids), "
            "('employee_id.parent_id.user_id', '=', user.id), "
            "('employee_id.user_id', '=', user.id), "
            "('user_id', '=', user.id)"
            "]",
        ),
    )
