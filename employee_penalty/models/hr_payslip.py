# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class InputLinePwnalty(models.Model):
    _inherit = 'hr.payslip.input'

    penalty_id = fields.Integer(help='refrence if the input line created by penalty')

class HrPayslipPenalty(models.Model):
    _inherit = 'hr.payslip'

    def _change_penalty_state(self,action):
        input_lines = self.input_line_ids.filtered_domain([('input_type_id','=',self.env.ref('employee_penalty.payslip_input_type_penalty').id)])
        if input_lines and action == 'discount':
            for ilp in input_lines:
                self.env['employee.penalty'].browse(ilp.penalty_id).action_discount()
        elif input_lines and action == 'approve':
            for ilp in input_lines:
                self.env['employee.penalty'].browse(ilp.penalty_id).action_approve()


    def compute_sheet(self):
        input_type_penalty_id = self.env.ref('employee_penalty.payslip_input_type_penalty').id
        penalties = self.env['employee.penalty'].search([
            ('employee_id','=',self.employee_id.id),
            ('state','=','approved'),
            ('month','=',str(self.date_from.month)),
            ('year','=',self.date_from.year)
            ])
        self.input_line_ids.search([('input_type_id','=',input_type_penalty_id)]).unlink()
        for penalty in penalties:
            self.input_line_ids.create({
                'payslip_id':self.id,
                'input_type_id':input_type_penalty_id,
                'amount':penalty.amount,
                'name':penalty.penalty_type_id.name,
                'penalty_id':penalty.id
            })
        return super().compute_sheet()

    def action_payslip_unpaid(self):
        res = super().action_payslip_unpaid()
        self._change_penalty_state('approve')
        return res 

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'paid':
            self._change_penalty_state('discount')
        if 'state' in vals and vals['state'] == 'cancel':
            self._change_penalty_state('approve')
        return super().write(vals)
