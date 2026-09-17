# -*- coding: utf-8 -*-


def migrate(cr, version):
    domain = (
        "['|', ('company_id', 'in', allowed_company_ids), "
        "('company_ids', 'in', allowed_company_ids)]"
    )
    domain_activities = (
        "['|', ('company_id', 'in', allowed_company_ids), "
        "('company_ids', 'in', allowed_company_ids), "
        "('activity_ids', '!=', False)]"
    )
    updates = {
        "open_view_employee_list_my": (domain, "{'chat_icon': True}"),
        "hr_employee_public_action": (domain, "{'chat_icon': True}"),
        "action_hr_employee_all_activities": (
            domain_activities,
            "{'chat_icon': True}",
        ),
    }
    for xmlid, (action_domain, context) in updates.items():
        cr.execute(
            """
            UPDATE ir_act_window
               SET domain = %s,
                   context = %s
             WHERE id = (
                SELECT res_id
                  FROM ir_model_data
                 WHERE module = 'hr'
                   AND name = %s
                   AND model = 'ir.actions.act_window'
             )
            """,
            (action_domain, context, xmlid),
        )
