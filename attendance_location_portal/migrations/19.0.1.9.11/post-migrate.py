# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api

# Removed portal fee-plan records. Order matters: views and access first,
# then record rules, then the group, then its privilege.
_XMLIDS = (
    "portal_my_home_menu_fee_plan",
    "portal_my_home_fee_plan_entry",
    "portal_student_fee_plan_failed_page",
    "portal_student_fee_plan_pay",
    "portal_my_fee_plans",
    "portal_student_fee_plan_new",
    "portal_student_fee_plan_detail",
    "portal_fee_installment_table",
    "portal_fee_other_table",
    "portal_student_fee_plan_exception",
    "access_student_fee_plan_portal_admin",
    "access_student_fee_installment_portal_admin",
    "access_student_fee_other_portal_admin",
    "access_bus_category_portal_fee_admin",
    "access_year_year_portal_fee_admin",
    "access_student_standard_portal_fee_admin",
    "access_standard_division_portal_fee_admin",
    "access_student_class_portal_fee_admin",
    "access_res_partner_portal_fee_admin",
    "access_account_journal_portal_fee_admin",
    "access_account_payment_method_line_portal_fee_admin",
    "access_account_move_portal_fee_admin",
    "access_account_payment_portal_fee_admin",
    "access_account_payment_register_portal_fee_admin",
    "student_fee_plan_portal_company_rule",
    "student_fee_installment_portal_company_rule",
    "student_fee_other_portal_company_rule",
    "group_portal_fee_admin",
    "privilege_portal_fee",
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for name in _XMLIDS:
        record = env.ref(
            "attendance_location_portal.%s" % name,
            raise_if_not_found=False,
        )
        if record:
            record.unlink()
