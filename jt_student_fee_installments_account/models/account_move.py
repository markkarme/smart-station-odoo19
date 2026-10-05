# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    student_fee_plan_id = fields.Many2one(
        'student.fee.plan',
        string='Student Fee Plan',
        copy=False,
        index=True,
        ondelete='set null',
    )
    student_fee_installment_id = fields.Many2one(
        'student.fee.installment',
        string='Fee Installment',
        copy=False,
        index=True,
        ondelete='set null',
    )
    student_fee_other_id = fields.Many2one(
        'student.fee.other',
        string='Other Fee',
        copy=False,
        index=True,
        ondelete='set null',
    )

    def write(self, vals):
        res = super().write(vals)
        # When payment_state becomes paid, sync back to fee lines
        if 'payment_state' in vals or vals.get('state') == 'posted':
            self._sync_student_fee_payment()
        return res

    def _sync_student_fee_payment(self):
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            # "in_payment" = payment registered (Bank journal) but not bank-reconciled yet.
            # For school fees we treat that as collected.
            if move.payment_state not in ('paid', 'in_payment'):
                continue
            if move.student_fee_installment_id:
                move.student_fee_installment_id._apply_invoice_payment_sync(move)
            if move.student_fee_other_id:
                move.student_fee_other_id._apply_invoice_payment_sync(move)
