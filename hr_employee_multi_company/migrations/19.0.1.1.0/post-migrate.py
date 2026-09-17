# -*- coding: utf-8 -*-


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    employees = env["hr.employee"].sudo().search([("user_id", "!=", False)])
    employees._sync_linked_user_companies()
