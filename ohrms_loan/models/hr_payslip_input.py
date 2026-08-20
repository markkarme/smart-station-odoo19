# -*- coding: utf-8 -*-
from odoo import fields, models


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    loan_line_id = fields.Many2one(
        'hr.loan.line',
        string="Loan Installment",
        help="Loan installment associated with this payslip input.",
    )
