# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.addons.school_molds_generator.models.default_columns import DEFAULT_COLUMNS

NEW_SUBJECT_KEYS = {
    'gr_subject', 'gr_work', 'gr_total',
    'pr_subject', 'pr_work', 'pr_total',
    'ai_subject', 'ai_work', 'ai_total',
}


def migrate(cr, version):
    """Add جرافيك / برمجة / ذكاء columns; المجموع الكلي max = 750."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Column = env['school.mold.column']
    new_cols = [col for col in DEFAULT_COLUMNS if col['key'] in NEW_SUBJECT_KEYS]

    for mold in env['school.mold'].search([]):
        existing = set(mold.column_ids.mapped('key'))
        if 'gr_subject' in existing:
            continue
        anchor = mold.column_ids.filtered(lambda c: c.key == 're_subject')[:1]
        if not anchor:
            anchor = mold.column_ids.filtered(lambda c: c.key == 'practical_total')[:1]
        if anchor:
            insert_at = anchor.sequence
            later = mold.column_ids.filtered(lambda c: c.sequence >= insert_at)
            for col in later.sorted('sequence', reverse=True):
                col.sequence += len(new_cols)
        else:
            insert_at = max(mold.column_ids.mapped('sequence') or [0]) + 1
        for offset, col in enumerate(new_cols):
            Column.create({
                'mold_id': mold.id,
                'sequence': insert_at + offset,
                'key': col['key'],
                'name': col['name'],
                'group_name': col['group_name'],
                'col_type': col['col_type'],
                'color': col['color'],
                'max_value': col['max_value'],
                'include_in_grand_total': col.get('include_in_grand_total', True),
            })

    Column.search([('key', '=', 'grand_total')]).write({'max_value': 750})
    Column.search([
        '|',
        ('key', 'in', ['re_subject', 're_work', 're_total']),
        ('group_name', '=', 'تربية دينية'),
    ]).write({'include_in_grand_total': False})
    env['school.mold.line'].search([])._recompute_totals()
