# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StudentFeePlan(models.Model):
    _inherit = 'student.fee.plan'

    invoice_count = fields.Integer(compute='_compute_invoice_count')

    def _compute_invoice_count(self):
        Move = self.env['account.move']
        for plan in self:
            plan.invoice_count = Move.search_count([
                ('student_fee_plan_id', '=', plan.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '!=', 'cancel'),
            ])

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('student_fee_plan_id', '=', self.id),
                ('move_type', '=', 'out_invoice'),
            ],
            'context': {
                'default_move_type': 'out_invoice',
                'default_partner_id': self.student_id.id,
                'default_student_fee_plan_id': self.id,
            },
        }

    def action_create_invoices_unpaid_basic(self):
        self.ensure_one()
        lines = self.basic_installment_ids.filtered(
            lambda l: (not l.invoice_id or l.invoice_id.state == 'cancel')
            and (l.amount_due or l.amount_paid)
        )
        if not lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invoices'),
                    'message': _('No basic installments ready to invoice.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return lines.action_create_invoice()

    def action_create_invoices_unpaid_bus(self):
        self.ensure_one()
        lines = self.bus_installment_ids.filtered(
            lambda l: (not l.invoice_id or l.invoice_id.state == 'cancel')
            and (l.amount_due or l.amount_paid)
        )
        if not lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invoices'),
                    'message': _('No bus installments ready to invoice.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return lines.action_create_invoice()
