# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class EmployeePenalty(models.Model):
    _name = 'employee.penalty'
    _description = 'EmployeePenalty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    penalty_type_id = fields.Many2one('penalty.type', string='Penalty Type', required=True,tracking=True)
    currency_id = fields.Many2one(related='penalty_type_id.currency_id')
    amount = fields.Monetary(related='penalty_type_id.amount', string='Amount of deduction', currency_field='currency_id')
    date = fields.Date('Date', default=fields.Date.today(), required=True)
    note = fields.Html('Note')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('discounted', 'Discounted')
    ], string='State', default='draft',tracking=True)
    month = fields.Selection([
        ('1','January'),
        ('2','February'),
        ('3','March'),
        ('4','April'),
        ('5','May'),
        ('6','June'),
        ('7','July'),
        ('8','August'),
        ('9','Septemper'),
        ('10','Octoper'),
        ('11','November'),
        ('11','Decemper'),
    ], compute="_compute_month", inverse="_inverse_month",store=True)
    year = fields.Integer(compute="_compute_year" ,store=True)

    @api.depends('employee_id','penalty_type_id')
    def _compute_display_name(self):
        self.display_name = f'{self.employee_id.name} - {self.penalty_type_id.name}'


    @api.constrains('date')
    def check_date(self):
        if self.date > fields.Date.today():
            raise ValidationError(_("You can not set penalty for date in feature"))

    @api.depends('date')
    def _compute_month(self):
        for record in self:
            if record.date:
                record.month = str(record.date.month)

    def _inverse_month(self):
        pass

    @api.depends('date')
    def _compute_year(self):
        for record in self:
            if record.date:
                record.year = str(record.date.year)

    def action_approve(self):
        for record in self:
            if record.state not in ('draft','discounted','approved'):
                raise UserError(_('You can only approve a draft record.'))
            record.write({'state': 'approved'})

    def action_reject(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('You can only reject a draft record.'))
            record.write({'state': 'rejected'})

    def action_cancel(self):
        for record in self:
            if record.state != 'approved':
                raise UserError(_('You can only cancel an approved record.'))
            paysilp_input = record.env['hr.payslip.input'].search([('penalty_id','=',record.id)], limit=1)
            if paysilp_input:
                if paysilp_input.payslip_id.state == 'draft':
                    paysilp_input.unlink()
                else:
                    raise UserError(_('There is deduction for this penalty in payslips.'))
            record.write({'state': 'cancelled'})

    def action_discount(self):
        for record in self:
            if record.state != 'approved':
                raise UserError(_('You can only discount an approved record.'))
            record.write({'state': 'discounted'})
