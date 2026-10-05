# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GenerateFeePlansWizard(models.TransientModel):
    _name = 'generate.fee.plans.wizard'
    _description = 'Generate Student Fee Plans'

    year_id = fields.Many2one('year.year', string='Academic Year', required=True)
    standard_id = fields.Many2one('student.standard', string='Standard (optional filter)')
    basic_installment_count = fields.Integer(
        string='Basic Installments',
        default=3,
    )
    bus_installment_count = fields.Integer(
        string='Bus Installments',
        default=2,
    )
    default_basic_total_due = fields.Float(
        string='Default Basic Total Dues',
        help='Used when the student standard has no fee amount.',
    )
    default_bus_total_due = fields.Float(string='Default Bus Total Dues')
    overwrite_due = fields.Boolean(
        string='Update totals / counts on existing plans',
        default=False,
    )
    student_count = fields.Integer(string='Students Found', compute='_compute_student_count')

    @api.depends('year_id', 'standard_id')
    def _compute_student_count(self):
        Partner = self.env['res.partner']
        for wizard in self:
            domain = [('is_student', '=', True)]
            if wizard.year_id:
                domain.append(('curr_year', '=', wizard.year_id.id))
            if wizard.standard_id:
                domain.append(('standard', '=', wizard.standard_id.id))
            wizard.student_count = Partner.search_count(domain) if wizard.year_id else 0

    @api.onchange('standard_id')
    def _onchange_standard_id(self):
        if self.standard_id and self.standard_id.fee:
            self.default_basic_total_due = self.standard_id.fee

    def action_generate(self):
        self.ensure_one()
        domain = [
            ('is_student', '=', True),
            ('curr_year', '=', self.year_id.id),
        ]
        if self.standard_id:
            domain.append(('standard', '=', self.standard_id.id))

        students = self.env['res.partner'].search(domain)
        if not students:
            raise UserError(_('No students found for the selected year/standard.'))

        Plan = self.env['student.fee.plan']
        created = 0
        updated = 0
        for student in students:
            plan = Plan.search([
                ('student_id', '=', student.id),
                ('year_id', '=', self.year_id.id),
            ], limit=1)
            basic_due = (
                student.standard.fee
                if student.standard and student.standard.fee
                else self.default_basic_total_due
            )
            vals = {
                'standard_id': student.standard.id,
                'division_id': student.div.id,
                'basic_installment_count': self.basic_installment_count,
                'bus_installment_count': self.bus_installment_count,
                'basic_total_due': basic_due or 0.0,
                'bus_total_due': self.default_bus_total_due or 0.0,
                'state': 'open',
            }
            if plan:
                if self.overwrite_due:
                    plan.write(vals)
                    updated += 1
                else:
                    plan.write({
                        'standard_id': student.standard.id,
                        'division_id': student.div.id,
                    })
                    updated += 1
            else:
                Plan.create({
                    'student_id': student.id,
                    'year_id': self.year_id.id,
                    **vals,
                })
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fee Plans'),
                'message': _(
                    'Created %(created)s plan(s), updated %(updated)s existing plan(s).',
                    created=created,
                    updated=updated,
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
