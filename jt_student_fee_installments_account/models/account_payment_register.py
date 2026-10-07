# -*- coding: utf-8 -*-
from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        res = super().action_create_payments()
        moves = self.env['account.move']
        if self.env.context.get('active_model') == 'account.move':
            moves = self.env['account.move'].browse(
                self.env.context.get('active_ids') or []
            )
        elif hasattr(self, 'line_ids'):
            moves = self.line_ids.mapped('move_id')
        moves._sync_student_fee_payment()
        return res
