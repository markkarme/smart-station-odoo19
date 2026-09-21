# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    columns = env['school.mold.column'].search([('key', 'in', ['total', 'grand_total', 'theory'])])
    for column in columns:
        if column.key == 'total':
            column.max_value = 300
        elif column.key == 'grand_total':
            column.max_value = 650
        elif column.key == 'theory':
            column.max_value = 80
    env['school.mold.line'].search([])._recompute_totals()
