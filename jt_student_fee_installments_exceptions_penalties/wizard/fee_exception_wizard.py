# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StudentFeeExceptionWizard(models.TransientModel):
    _name = 'student.fee.exception.wizard'
    _description = 'معالج استثناء رسوم الطلاب'

    plan_id = fields.Many2one(
        'student.fee.plan',
        string='خطة الرسوم',
        required=True,
        ondelete='cascade',
    )
    student_id = fields.Many2one(related='plan_id.student_id', readonly=True)
    exception_type = fields.Selection(
        [
            ('increase_installments', 'زيادة عدد الأقساط'),
            ('discount', 'خصم'),
            ('change_due_date', 'تعديل موعد الاستحقاق'),
        ],
        string='نوع الاستثناء',
        required=True,
        default='increase_installments',
    )

    # Increase installments
    fee_type = fields.Selection(
        [
            ('basic', 'أقساط المصاريف الدراسية'),
            ('bus', 'أقساط الباصات'),
        ],
        string='التطبيق على',
        default='basic',
    )
    current_installment_count = fields.Integer(
        string='عدد الأقساط الحالي',
        compute='_compute_current_installment_count',
    )
    new_installment_count = fields.Integer(string='عدد الأقساط الجديد')

    # Discount
    discount_type = fields.Selection(
        [
            ('fixed', 'مبلغ ثابت'),
            ('percent', 'نسبة مئوية'),
        ],
        string='نوع الخصم',
        default='fixed',
    )
    discount_value = fields.Float(string='قيمة الخصم')
    installment_ids = fields.Many2many(
        'student.fee.installment',
        'student_fee_exception_wizard_installment_rel',
        'wizard_id',
        'installment_id',
        string='الأقساط غير المسددة',
        domain="[('plan_id', '=', plan_id), ('is_paid', '=', False)]",
    )

    # Change due date
    new_due_date = fields.Date(string='موعد الاستحقاق الجديد')

    document = fields.Binary(string='المستند الداعم', required=True)
    document_filename = fields.Char(string='اسم الملف')
    reason = fields.Text(string='ملاحظات')

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
        self.new_due_date = False
        if self.exception_type == 'increase_installments':
            self.discount_value = 0.0
            self._onchange_fee_type()

    def action_confirm(self):
        self.ensure_one()
        if not self.document:
            raise UserError(_('يرجى رفع مستند داعم.'))

        plan = self.plan_id
        Exception = self.env['student.fee.exception']

        if self.exception_type == 'increase_installments':
            if not self.fee_type:
                raise UserError(_('يرجى اختيار أقساط المصاريف أو الباصات.'))
            if self.new_installment_count <= self.current_installment_count:
                raise ValidationError(_(
                    'يجب أن يكون عدد الأقساط الجديد أكبر من العدد الحالي (%s).',
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
                'تم تطبيق استثناء: زيادة %(fee)s إلى %(count)s قسط.',
                fee=dict(self._fields['fee_type'].selection).get(self.fee_type),
                count=self.new_installment_count,
            ))

        elif self.exception_type == 'discount':
            if not self.installment_ids:
                raise UserError(_('يرجى اختيار الأقساط غير المسددة لتطبيق الخصم.'))
            if not self.discount_type:
                raise UserError(_('يرجى اختيار نوع الخصم.'))
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
                'تم تطبيق استثناء: خصم %(dtype)s بقيمة %(value)s على %(count)s قسط غير مسدد.',
                dtype=dict(self._fields['discount_type'].selection).get(self.discount_type),
                value=self.discount_value,
                count=len(self.installment_ids),
            ))

        elif self.exception_type == 'change_due_date':
            if not self.installment_ids:
                raise UserError(_(
                    'يرجى اختيار الأقساط لتعديل موعد الاستحقاق.'
                ))
            if not self.new_due_date:
                raise UserError(_('يرجى تحديد موعد الاستحقاق الجديد.'))
            plan.action_apply_change_due_date(
                self.installment_ids.ids,
                self.new_due_date,
            )
            Exception.create({
                'plan_id': plan.id,
                'exception_type': 'change_due_date',
                'new_due_date': self.new_due_date,
                'installment_ids': [(6, 0, self.installment_ids.ids)],
                'document': self.document,
                'document_filename': self.document_filename,
                'reason': self.reason,
            })
            plan.message_post(body=_(
                'تم تطبيق استثناء: تعديل موعد الاستحقاق إلى %(date)s على %(count)s قسط.',
                date=self.new_due_date,
                count=len(self.installment_ids),
            ))
        else:
            raise UserError(_('نوع الاستثناء غير صالح.'))

        return {'type': 'ir.actions.act_window_close'}
