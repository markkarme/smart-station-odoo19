def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    for model_name in ("hr.general.request", "hr.attendance.adjustment.request"):
        records = env[model_name].search([("state", "=", "confirm")])
        if records:
            records.activity_update()
