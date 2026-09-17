# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Point attendance multi-company rule at attendance.company_id (location company)."""
    cr.execute(
        """
        UPDATE hr_attendance AS a
           SET company_id = loc.company_id
          FROM attendance_location AS loc
         WHERE loc.id = a.attendance_location_id
           AND a.company_id IS DISTINCT FROM loc.company_id
        """
    )
    cr.execute(
        """
        UPDATE ir_rule
           SET name = %s,
               domain_force = %s
         WHERE id = (
            SELECT res_id
              FROM ir_model_data
             WHERE module = 'hr_attendance'
               AND name = 'hr_attendance_rule_employee_company'
               AND model = 'ir.rule'
         )
        """,
        (
            "Attendance multi company rule (by location company)",
            "['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]",
        ),
    )
