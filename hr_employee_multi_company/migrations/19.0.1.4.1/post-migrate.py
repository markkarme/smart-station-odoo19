# -*- coding: utf-8 -*-


def migrate(cr, version):
    # Restore search view: searchpanel category cannot use many2many.
    # Re-load arch from module XML on next -u; also clear broken customization
    # if the searchpanel field was renamed to company_ids.
    cr.execute(
        """
        UPDATE ir_ui_view
           SET arch_db = replace(arch_db::text, 'name=\"company_ids\"', 'name=\"company_id\"')::jsonb
         WHERE id IN (
            SELECT res_id FROM ir_model_data
             WHERE module = 'hr_employee_multi_company'
               AND name = 'view_employee_filter_multi_company'
         )
           AND arch_db::text LIKE '%searchpanel%company_ids%'
        """
    )
