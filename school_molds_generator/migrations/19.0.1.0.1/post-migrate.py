# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    molds = env['school.mold'].search([])
    if molds:
        molds._apply_first_term_layout()
