# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StudentFeeException(models.Model):
    _name = 'student.fee.exception'
    _description = 'Student Fee Exception'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='المرجع', required=True, copy=False, default=lambda self: _('جديد'))
    plan_id = fields.Many2one(
        'student.fee.plan',
        string='خطة الرسوم',
        required=True,
        ondelete='cascade',
        index=True,
    )
    student_id = fields.Many2one(related='plan_id.student_id', store=True, readonly=True)
    year_id = fields.Many2one(related='plan_id.year_id', store=True, readonly=True)
    exception_type = fields.Selection(
        [
            ('increase_installments', 'زيادة عدد الأقساط'),
            ('discount', 'خصم'),
            ('change_due_date', 'تعديل موعد الاستحقاق'),
        ],
        string='نوع الاستثناء',
        required=True,
        tracking=True,
    )
    new_due_date = fields.Date(string='موعد الاستحقاق الجديد')
    fee_type = fields.Selection(
        [
            ('basic', 'أقساط المصاريف الدراسية'),
            ('bus', 'أقساط الباصات'),
        ],
        string='نوع القسط',
    )
    new_installment_count = fields.Integer(string='عدد الأقساط الجديد')
    discount_type = fields.Selection(
        [
            ('fixed', 'مبلغ ثابت'),
            ('percent', 'نسبة مئوية'),
        ],
        string='نوع الخصم',
    )
    discount_value = fields.Float(string='قيمة الخصم')
    installment_ids = fields.Many2many(
        'student.fee.installment',
        'student_fee_exception_installment_rel',
        'exception_id',
        'installment_id',
        string='الأقساط المتأثرة',
    )
    document = fields.Binary(string='المستند الداعم', attachment=True, required=True)
    document_filename = fields.Char(string='اسم الملف')
    reason = fields.Text(string='السبب')
    user_id = fields.Many2one(
        'res.users',
        string='بواسطة',
        default=lambda self: self.env.user,
        required=True,
    )
    state = fields.Selection(
        [('done', 'تم التطبيق')],
        default='done',
        string='الحالة',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('جديد')) == _('جديد'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'student.fee.exception'
                ) or _('استثناء')
        return super().create(vals_list)
