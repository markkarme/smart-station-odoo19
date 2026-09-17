# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Share resource.resource for multi-company employees (company_id=False)."""
    cr.execute(
        """
        UPDATE resource_resource AS r
           SET company_id = NULL
          FROM hr_employee AS e
         WHERE e.resource_id = r.id
           AND r.company_id IS NOT NULL
           AND (
                SELECT COUNT(*)
                  FROM hr_employee_res_company_rel AS rel
                 WHERE rel.employee_id = e.id
           ) > 1
        """
    )
