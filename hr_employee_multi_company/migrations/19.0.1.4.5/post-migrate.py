# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Allow reading hr.version when the employee belongs to an active company.

    Versions keep company_id = employee main company. Multi-company employees
    visible in another company (e.g. ملوي) still have versions on the main
    company (e.g. مدرسة سمارت للتمريض), which blocked Attendances/Employees.
    """
    cr.execute(
        """
        UPDATE ir_rule
           SET name = %s,
               domain_force = %s
         WHERE id = (
            SELECT res_id
              FROM ir_model_data
             WHERE module = 'hr'
               AND name = 'ir_rule_hr_contract_multi_company'
               AND model = 'ir.rule'
         )
        """,
        (
            "HR Contract: Multi Company (employee companies)",
            "["
            "'|', "
            "('company_id', 'in', company_ids), "
            "('employee_id.company_ids', 'in', company_ids)"
            "]",
        ),
    )
