from odoo import SUPERUSER_ID


def decision_user(record):
    """Return the logged-in user, including portal approvals that run with sudo()."""
    if not record.env.su:
        return record.env.user
    try:
        from odoo.http import request

        http_env = request.env
    except RuntimeError:
        return record.env.user
    if http_env.uid and http_env.uid != SUPERUSER_ID:
        return http_env.user
    return record.env.user
