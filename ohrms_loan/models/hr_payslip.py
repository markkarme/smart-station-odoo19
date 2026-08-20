# -*- coding: utf-8 -*-
from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _ohrms_loan_input_type(self):
        return self.env.ref('ohrms_loan.payslip_input_type_loan')

    def _prepare_loan_input_lines(self):
        self.ensure_one()
        input_type = self._ohrms_loan_input_type()
        total_loan_amount = 0.0
        first_loan_line_id = False
        loans = self.env['hr.loan'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'approve'),
        ])
        for loan in loans:
            for loan_line in loan.loan_lines:
                if self.date_from <= loan_line.date <= self.date_to and not loan_line.paid:
                    total_loan_amount += loan_line.amount
                    if not first_loan_line_id:
                        first_loan_line_id = loan_line.id
        if not total_loan_amount:
            return []
        return [{
            'input_type_id': input_type.id,
            'amount': total_loan_amount,
            'name': 'Loan Installment',
            'loan_line_id': first_loan_line_id,
        }]

    def compute_sheet(self):
        loan_input_type = self.env.ref('ohrms_loan.payslip_input_type_loan', raise_if_not_found=False)
        if loan_input_type:
            for payslip in self:
                payslip.input_line_ids.filtered(
                    lambda line: line.input_type_id == loan_input_type
                ).unlink()
                for vals in payslip._prepare_loan_input_lines():
                    vals['payslip_id'] = payslip.id
                    self.env['hr.payslip.input'].create(vals)
        return super().compute_sheet()

    def action_payslip_done(self):
        for payslip in self:
            if payslip.input_line_ids.filtered(lambda line: line.code == 'LO'):
                loans = self.env['hr.loan'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('state', '=', 'approve'),
                ])
                for loan in loans:
                    for loan_line in loan.loan_lines:
                        if payslip.date_from <= loan_line.date <= payslip.date_to and not loan_line.paid:
                            loan_line.paid = True
                            loan_line.loan_id._compute_total_amount()
        return super().action_payslip_done()
