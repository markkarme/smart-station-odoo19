# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    mold_result_ids = fields.One2many(
        'school.mold.line',
        'student_id',
        string='Grades Record',
    )
    mold_result_count = fields.Integer(
        string='Grades Count',
        compute='_compute_mold_result_count',
    )

    def _compute_mold_result_count(self):
        Line = self.env['school.mold.line']
        for partner in self:
            partner.mold_result_count = Line.search_count([
                ('student_id', '=', partner.id),
                ('mold_id.state', '=', 'done'),
                ('mold_id.mold_kind', '=', 'grades'),
            ])

    def action_view_mold_results(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('سجل الدرجات - %s') % (self.display_name or self.name),
            'res_model': 'school.mold.line',
            'view_mode': 'list,form',
            'domain': [
                ('student_id', '=', self.id),
                ('mold_id.state', '=', 'done'),
                ('mold_id.mold_kind', '=', 'grades'),
            ],
            'context': {
                'default_student_id': self.id,
                'create': False,
                'edit': False,
                'delete': False,
            },
            'views': [
                (self.env.ref('school_molds_generator.school_mold_line_result_view_list').id, 'list'),
                (self.env.ref('school_molds_generator.school_mold_line_result_view_form').id, 'form'),
            ],
        }
