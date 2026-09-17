# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Ensure searchpanel never uses many2many company_ids."""
    cr.execute(
        """
        UPDATE ir_ui_view
           SET arch_db = replace(
                arch_db::text,
                'name="company_ids"',
                'name="company_id"'
           )::jsonb
         WHERE model IN ('hr.employee', 'hr.employee.public')
           AND arch_db::text LIKE '%searchpanel%'
           AND arch_db::text LIKE '%name="company_ids"%'
        """
    )
    # Also fix JSON-escaped form used in arch_db
    cr.execute(
        """
        UPDATE ir_ui_view
           SET arch_db = replace(
                arch_db::text,
                'name=\\"company_ids\\"',
                'name=\\"company_id\\"'
           )::jsonb
         WHERE model IN ('hr.employee', 'hr.employee.public')
           AND arch_db::text LIKE '%searchpanel%'
           AND arch_db::text LIKE '%company_ids%'
        """
    )
