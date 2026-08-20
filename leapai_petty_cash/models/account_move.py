from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    petty_cash_fund_id = fields.Many2one(
        'petty.cash.fund', string='Petty Cash Fund', copy=False, index=True)
