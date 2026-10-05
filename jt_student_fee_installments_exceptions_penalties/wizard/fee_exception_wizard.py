# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StudentFeeExceptionWizard(models.TransientModel):
    _name = 'student.fee.exception.wizard'
    _description = 'Student Fee Exception Wizard'

    plan_id = fields.Many2one(
        'student.fee.plan',
        string='Fee Plan',
        required=True,
        ondelete='cascade',
    )
    student_id = fields.Many2one(related='plan_id.student_id', readonly=True)
    exception_type = fields.Selection(
        [
            ('increase_installments', 'Increase Number of Installments / زيادة عدد الأقساط'),
            ('discount', 'Discount / خصم'),
        ],
        string='Exception Type',
        required=True,
        default='increase_installments',
    )

    # Increase installments
    fee_type = fields.Selection(
        [
            ('basic', 'أقساط المصاريف الأساسية'),
            ('bus', 'أقساط الباصات'),
        ],
        string='Apply On',
        default='basic',
    )
    current_installment_count = fields.Integer(
        string='Current Installments',
        compute='_compute_current_installment_count',
    )
    new_installment_count = fields.Integer(string='New Number of Installments')

    # Discount
    discount_type = fields.Selection(
        [
            ('fixed', 'Fixed Amount / مبلغ ثابت'),
            ('percent', 'Percentage / نسبة مئوية'),
        ],
        string='Discount Type',
        default='fixed',
    )
    discount_value = fields.Float(string='Discount Value')
    installment_ids = fields.Many2many(
        'student.fee.installment',
        'student_fee_exception_wizard_installment_rel',
        'wizard_id',
        'installment_id',
        string='Unpaid Installments',
        domain="[('plan_id', '=', plan_id), ('is_paid', '=', False)]",
    )

    document = fields.Binary(string='Supporting Document', required=True)
    document_filename = fields.Char(string='Filename')
    reason = fields.Text(string='Reason / ملاحظات')

    @api.depends('plan_id', 'fee_type')
    def _compute_current_installment_count(self):
        for wiz in self:
            if not wiz.plan_id or not wiz.fee_type:
                wiz.current_installment_count = 0
                continue
            if wiz.fee_type == 'basic':
                wiz.current_installment_count = wiz.plan_id.basic_installment_count
            else:
                wiz.current_installment_count = wiz.plan_id.bus_installment_count

    @api.onchange('fee_type', 'plan_id')
    def _onchange_fee_type(self):
        if self.exception_type == 'increase_installments' and self.plan_id:
            self.new_installment_count = self.current_installment_count + 1

    @api.onchange('exception_type')
    def _onchange_exception_type(self):
        self.installment_ids = False
        if self.exception_type == 'increase_installments':
            self.discount_value = 0.0
            self._onchange_fee_type()

    def action_confirm(self):
        self.ensure_one()
        if not self.document:
            raise UserError(_('Please upload a supporting document.'))

        plan = self.plan_id
        Exception = self.env['student.fee.exception']

        if self.exception_type == 'increase_installments':
            if not self.fee_type:
                raise UserError(_('Please select basic or bus installments.'))
            if self.new_installment_count <= self.current_installment_count:
                raise ValidationError(_(
                    'New installment count must be greater than the current count (%s).',
                    self.current_installment_count,
                ))
            plan.action_apply_increase_installments(self.fee_type, self.new_installment_count)
            Exception.create({
                'plan_id': plan.id,
                'exception_type': 'increase_installments',
                'fee_type': self.fee_type,
                'new_installment_count': self.new_installment_count,
                'document': self.document,
                'document_filename': self.document_filename,
                'reason': self.reason,
            })
            plan.message_post(body=_(
                'Exception applied: increase %(fee)s installments to %(count)s.',
                fee=dict(self._fields['fee_type'].selection).get(self.fee_type),
                count=self.new_installment_count,
            ))

        elif self.exception_type == 'discount':
            if not self.installment_ids:
                raise UserError(_('Please select the unpaid installment line(s) for the discount.'))
            if not self.discount_type:
                raise UserError(_('Please select the discount type.'))
            plan.action_apply_discount(
                self.installment_ids.ids,
                self.discount_type,
                self.discount_value,
            )
            Exception.create({
                'plan_id': plan.id,
                'exception_type': 'discount',
                'discount_type': self.discount_type,
                'discount_value': self.discount_value,
                'installment_ids': [(6, 0, self.installment_ids.ids)],
                'document': self.document,
                'document_filename': self.document_filename,
                'reason': self.reason,
            })
            plan.message_post(body=_(
                'Exception applied: %(dtype)s discount %(value)s on %(count)s unpaid installment(s).',
                dtype=dict(self._fields['discount_type'].selection).get(self.discount_type),
                value=self.discount_value,
                count=len(self.installment_ids),
            ))
        else:
            raise UserError(_('Invalid exception type.'))

        return {'type': 'ir.actions.act_window_close'}
