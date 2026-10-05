# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StudentFeeOther(models.Model):
    _name = 'student.fee.other'
    _description = 'Student Other Fee'
    _order = 'fee_type, payment_date, id'

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
            ('books', 'الكتب'),
            ('uniform', 'اليونيفورم'),
        ],
        string='Fee Type',
        required=True,
        index=True,
    )
    amount = fields.Monetary(
        string='Amount / المبلغ',
        currency_field='currency_id',
        required=True,
    )
    receipt_number = fields.Char(string='Receipt No / رقم الإيصال')
    payment_date = fields.Date(
        string='Date / التاريخ',
        default=fields.Date.context_today,
    )
    note = fields.Char(string='Note')
    name = fields.Char(compute='_compute_name', store=True)
    is_paid = fields.Boolean(
        string='Paid',
        compute='_compute_is_paid',
        store=True,
    )

    @api.depends('fee_type', 'receipt_number', 'amount')
    def _compute_name(self):
        labels = dict(self._fields['fee_type'].selection)
        for line in self:
            label = labels.get(line.fee_type, '')
            line.name = '%s — %s (%s)' % (
                label,
                line.amount or 0.0,
                line.receipt_number or '',
            )

    @api.depends('amount', 'payment_date')
    def _compute_is_paid(self):
        """Without accounting: paid when amount and date are set."""
        for line in self:
            line.is_paid = bool(line.amount) and bool(line.payment_date)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('receipt_number'):
                vals['receipt_number'] = sequence.next_by_code(
                    'student.fee.payment.receipt'
                ) or _('New')
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount < 0:
                raise ValidationError(_('Amount cannot be negative.'))
