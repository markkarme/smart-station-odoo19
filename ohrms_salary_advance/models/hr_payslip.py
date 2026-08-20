# -*- coding: utf-8 -*-
from odoo import models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _ohrms_advance_input_type(self):
        return self.env.ref('ohrms_salary_advance.payslip_input_type_advance')

    def _prepare_advance_input_lines(self):
        self.ensure_one()
        input_type = self._ohrms_advance_input_type()
        advances = self.env['salary.advance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'approve'),
        ])
        lines_vals = []
        for advance in advances:
            if (
                advance.date
                and self.date_from
                and advance.date.month == self.date_from.month
                and advance.date.year == self.date_from.year
            ):
                lines_vals.append({
                    'input_type_id': input_type.id,
                    'amount': advance.advance,
                    'name': advance.name or 'Salary Advance',
                })
        return lines_vals

    def compute_sheet(self):
        advance_input_type = self.env.ref(
            'ohrms_salary_advance.payslip_input_type_advance',
            raise_if_not_found=False,
        )
        if advance_input_type:
            for payslip in self:
                payslip.input_line_ids.filtered(
                    lambda line: line.input_type_id == advance_input_type
                ).unlink()
                for vals in payslip._prepare_advance_input_lines():
                    vals['payslip_id'] = payslip.id
                    self.env['hr.payslip.input'].create(vals)
        return super().compute_sheet()
