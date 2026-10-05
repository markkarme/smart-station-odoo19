# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StudentFeeOther(models.Model):
    _name = 'student.fee.other'
    _inherit = ['student.fee.other', 'student.fee.accounting.mixin']

    def _fee_accounting_category(self):
        self.ensure_one()
        return self.fee_type

    def _fee_accounting_amount(self):
        self.ensure_one()
        return self.amount or 0.0

    def _fee_accounting_description(self):
        self.ensure_one()
        labels = dict(self._fields['fee_type'].selection)
        student = self.student_id.name or ''
        year = self.year_id.name or ''
        return _(
            '%(fee)s — %(student)s (%(year)s)',
            fee=labels.get(self.fee_type, self.fee_type),
            student=student,
            year=year,
        )

    def _fee_accounting_date(self):
        self.ensure_one()
        return self.payment_date or fields.Date.context_today(self)

    def _invoice_link_vals(self):
        self.ensure_one()
        return {
            'student_fee_other_id': self.id,
            'student_fee_plan_id': self.plan_id.id,
        }

    @api.depends(
        'amount',
        'payment_date',
        'invoice_id',
        'invoice_id.payment_state',
        'invoice_id.state',
    )
    def _compute_is_paid(self):
        """Books/uniform count as paid only when the linked invoice is paid."""
        for line in self:
            if line.invoice_id and line.invoice_id.state != 'cancel':
                line.is_paid = line.invoice_id.payment_state in ('paid', 'in_payment')
            else:
                line.is_paid = False

    def _apply_invoice_payment_sync(self, invoice):
        for line in self:
            vals = {
                'amount': invoice.amount_total,
                'payment_date': invoice.invoice_date or fields.Date.context_today(self),
            }
            if not line.receipt_number:
                vals['receipt_number'] = invoice.ref or invoice.name
            line.with_context(skip_fee_invoice_sync=True).write(vals)
