# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StudentFeeInstallment(models.Model):
    _name = 'student.fee.installment'
    _description = 'Student Fee Installment'
    _order = 'fee_type, number, id'

    plan_id = fields.Many2one(
        'student.fee.plan',
        string='Fee Plan',
        required=True,
        ondelete='cascade',
        index=True,
    )
    student_id = fields.Many2one(
        related='plan_id.student_id',
        store=True,
        readonly=True,
    )
    year_id = fields.Many2one(
        related='plan_id.year_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='plan_id.currency_id',
        store=True,
        readonly=True,
    )
    fee_type = fields.Selection(
        [
            ('basic', 'أقساط المصاريف الأساسية'),
            ('bus', 'أقساط الباصات'),
        ],
        string='Installment Type',
        required=True,
        index=True,
    )
    number = fields.Integer(string='Installment No', required=True, default=1)
    name = fields.Char(string='Label', compute='_compute_name', store=True)
    amount_due = fields.Monetary(
        string='Amount Due / المستحق',
        currency_field='currency_id',
    )
    amount_paid = fields.Monetary(
        string='Amount Paid / المبلغ',
        currency_field='currency_id',
    )
    receipt_number = fields.Char(string='Receipt No / رقم الإيصال')
    payment_date = fields.Date(string='Date / التاريخ')
    note = fields.Char(string='Note')
    is_paid = fields.Boolean(
        string='Paid',
        compute='_compute_is_paid',
        store=True,
    )

    _sql_constraints = [
        (
            'plan_type_number_uniq',
            'unique(plan_id, fee_type, number)',
            'Installment number must be unique per type on the same fee plan.',
        ),
    ]

    @api.depends('fee_type', 'number')
    def _compute_name(self):
        labels = {
            'basic': _('القسط %s — مصاريف أساسية'),
            'bus': _('القسط %s — باصات'),
        }
        for line in self:
            template = labels.get(line.fee_type, _('Installment %s'))
            line.name = template % (line.number or 0)

    @api.depends('amount_paid', 'amount_due')
    def _compute_is_paid(self):
        for line in self:
            line.is_paid = bool(line.amount_paid) and (
                not line.amount_due or line.amount_paid >= line.amount_due
            )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('amount_paid'):
                if not vals.get('receipt_number'):
                    vals['receipt_number'] = sequence.next_by_code(
                        'student.fee.payment.receipt'
                    ) or _('New')
                if not vals.get('payment_date'):
                    vals['payment_date'] = fields.Date.context_today(self)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if vals.get('amount_paid'):
            if 'receipt_number' not in vals:
                for line in self:
                    if not line.receipt_number:
                        vals['receipt_number'] = self.env['ir.sequence'].next_by_code(
                            'student.fee.payment.receipt'
                        ) or _('New')
                        break
            if 'payment_date' not in vals:
                for line in self:
                    if not line.payment_date:
                        vals['payment_date'] = fields.Date.context_today(self)
                        break
        return super().write(vals)

    @api.constrains('number', 'amount_due', 'amount_paid')
    def _check_amounts(self):
        for line in self:
            if line.number < 1:
                raise ValidationError(_('Installment number must be at least 1.'))
            if line.amount_due < 0 or line.amount_paid < 0:
                raise ValidationError(_('Amounts cannot be negative.'))
