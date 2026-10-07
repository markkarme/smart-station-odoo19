# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StudentFeeInstallment(models.Model):
    _name = 'student.fee.installment'
    _inherit = ['student.fee.installment', 'student.fee.accounting.mixin']

    def _fee_accounting_category(self):
        self.ensure_one()
        return self.fee_type

    def _fee_accounting_amount(self):
        self.ensure_one()
        return self.amount_due or self.amount_paid or 0.0

    def _fee_accounting_description(self):
        self.ensure_one()
        student = self.student_id.name or ''
        year = self.year_id.name or ''
        return _('%(label)s — %(student)s (%(year)s)', label=self.name, student=student, year=year)

    def _fee_accounting_date(self):
        self.ensure_one()
        return self.payment_date or fields.Date.context_today(self)

    def _invoice_link_vals(self):
        self.ensure_one()
        return {
            'student_fee_installment_id': self.id,
            'student_fee_plan_id': self.plan_id.id,
        }

    @api.depends('amount_paid', 'amount_due', 'invoice_id', 'invoice_id.payment_state', 'invoice_id.state')
    def _compute_is_paid(self):
        """With accounting: collected when invoice is paid or in payment (bank outstanding)."""
        for line in self:
            if line.invoice_id and line.invoice_id.state != 'cancel':
                line.is_paid = line.invoice_id.payment_state in ('paid', 'in_payment')
            else:
                line.is_paid = bool(line.amount_paid) and (
                    not line.amount_due or line.amount_paid >= line.amount_due
                )

    def _apply_invoice_payment_sync(self, invoice):
        for line in self:
            vals = {
                'amount_paid': invoice.amount_total,
                'payment_date': invoice.invoice_date or fields.Date.context_today(self),
            }
            if not line.receipt_number:
                vals['receipt_number'] = invoice.ref or invoice.name
            line.with_context(skip_fee_invoice_sync=True).write(vals)
