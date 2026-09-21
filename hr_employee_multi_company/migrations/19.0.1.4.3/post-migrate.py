# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Restore resource.company_id from employee main company.

    Earlier versions cleared resource.company_id for multi-company employees,
    which also cleared hr.employee.company_id (related field) and broke saves.
    """
    cr.execute(
        """
        UPDATE resource_resource AS r
           SET company_id = e.company_id
          FROM hr_employee AS e
         WHERE e.resource_id = r.id
           AND r.company_id IS NULL
           AND e.company_id IS NOT NULL
        """
    )
