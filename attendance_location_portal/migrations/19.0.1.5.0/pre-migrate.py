# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Ensure company_id exists and is filled from the attendance location."""
    cr.execute(
        """
        ALTER TABLE hr_attendance
        ADD COLUMN IF NOT EXISTS company_id integer
        """
    )
    cr.execute(
        """
        UPDATE hr_attendance AS a
           SET company_id = COALESCE(
                (SELECT l.company_id
                   FROM attendance_location AS l
                  WHERE l.id = a.attendance_location_id),
                (SELECT e.company_id
                   FROM hr_employee AS e
                  WHERE e.id = a.employee_id)
           )
         WHERE a.company_id IS NULL
            OR (
                a.attendance_location_id IS NOT NULL
                AND a.company_id IS DISTINCT FROM (
                    SELECT l.company_id
                      FROM attendance_location AS l
                     WHERE l.id = a.attendance_location_id
                )
            )
        """
    )
