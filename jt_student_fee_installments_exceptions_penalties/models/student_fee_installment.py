# -*- coding: utf-8 -*-
import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StudentFeeInstallment(models.Model):
    _inherit = 'student.fee.installment'

    due_date = fields.Date(
        string='Due Date / تاريخ الاستحقاق',
        index=True,
        help='Installment due date. Late weeks are counted after this date. Readonly once paid.',
    )
    amount_due_original = fields.Monetary(
        string='Original Amount Due',
        currency_field='currency_id',
        help='Amount before any discount exception.',
        copy=False,
    )
    weeks_late = fields.Integer(
        string='Weeks Late',
        compute='_compute_penalty',
    )
    penalty_amount = fields.Monetary(
        string='Late Penalty / غرامة التأخير',
        currency_field='currency_id',
        compute='_compute_penalty',
    )
    amount_with_penalty = fields.Monetary(
        string='Total to Collect',
        currency_field='currency_id',
        compute='_compute_penalty',
        help='Amount due + late penalty.',
    )
    penalty_waived = fields.Boolean(
        string='Penalty Waived',
        default=False,
        copy=False,
    )

    @api.depends(
        'due_date',
        'is_paid',
        'payment_date',
        'amount_due',
        'penalty_waived',
        'plan_id.penalty_price_per_week',
    )
    def _compute_penalty(self):
        today = fields.Date.context_today(self)
        for line in self:
            if line.penalty_waived or not line.due_date:
                line.weeks_late = 0
                line.penalty_amount = 0.0
                line.amount_with_penalty = line.amount_due or 0.0
                continue

            if line.is_paid:
                ref_date = line.payment_date or today
            else:
                ref_date = today

            if ref_date <= line.due_date:
                weeks = 0
            else:
                days = (ref_date - line.due_date).days
                weeks = int(math.ceil(days / 7.0))

            price = line.plan_id.penalty_price_per_week if line.plan_id else 50.0
            penalty = weeks * (price or 0.0)
            line.weeks_late = weeks
            line.penalty_amount = penalty
            line.amount_with_penalty = (line.amount_due or 0.0) + penalty

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('amount_due') and not vals.get('amount_due_original'):
                vals['amount_due_original'] = vals['amount_due']
        return super().create(vals_list)

    def write(self, vals):
        if 'due_date' in vals and any(line.is_paid for line in self):
            raise UserError(_(
                'You cannot change the due date (تاريخ الاستحقاق) on a paid installment.'
            ))
        if 'amount_due' in vals and 'amount_due_original' not in vals:
            to_init = self.filtered(lambda l: not l.amount_due_original)
            if to_init and vals.get('amount_due'):
                super(StudentFeeInstallment, to_init).write({
                    'amount_due_original': vals['amount_due'],
                })
        return super().write(vals)
