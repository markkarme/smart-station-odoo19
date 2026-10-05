# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    fee_plan_ids = fields.One2many(
        'student.fee.plan',
        'student_id',
        string='Fee Plans',
    )
    fee_plan_count = fields.Integer(
        string='Installments',
        compute='_compute_fee_plan_count',
    )

    def _compute_fee_plan_count(self):
        Plan = self.env['student.fee.plan']
        for partner in self:
            partner.fee_plan_count = Plan.search_count([
                ('student_id', '=', partner.id),
            ]) if partner.is_student else 0

    def action_view_fee_plans(self):
        """Quick access to this student's installment fee plan(s)."""
        self.ensure_one()
        context = {
            'default_student_id': self.id,
            'default_year_id': self.curr_year.id if self.curr_year else False,
            'default_standard_id': self.standard.id if self.standard else False,
            'default_division_id': self.div.id if self.div else False,
            'default_basic_total_due': self.standard.fee if self.standard else 0.0,
            'default_state': 'open',
        }
        plans = self.env['student.fee.plan'].search([
            ('student_id', '=', self.id),
        ])

        action = {
            'name': _('Installments'),
            'type': 'ir.actions.act_window',
            'res_model': 'student.fee.plan',
            'domain': [('student_id', '=', self.id)],
            'context': context,
            'target': 'current',
        }

        if len(plans) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': plans.id,
            })
        elif not plans:
            # Open a new fee plan form prefilled for this student
            action.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
            })
        else:
            action['view_mode'] = 'list,form'

        return action
