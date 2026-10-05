# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StudentFeeException(models.Model):
    _name = 'student.fee.exception'
    _description = 'Student Fee Exception'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'))
    plan_id = fields.Many2one(
        'student.fee.plan',
        string='Fee Plan',
        required=True,
        ondelete='cascade',
        index=True,
    )
    student_id = fields.Many2one(related='plan_id.student_id', store=True, readonly=True)
    year_id = fields.Many2one(related='plan_id.year_id', store=True, readonly=True)
    exception_type = fields.Selection(
        [
            ('increase_installments', 'Increase Number of Installments'),
            ('discount', 'Discount'),
        ],
        string='Exception Type',
        required=True,
        tracking=True,
    )
    fee_type = fields.Selection(
        [
            ('basic', 'أقساط المصاريف الأساسية'),
            ('bus', 'أقساط الباصات'),
        ],
        string='Installment Type',
    )
    new_installment_count = fields.Integer(string='New Installment Count')
    discount_type = fields.Selection(
        [
            ('fixed', 'Fixed Amount'),
            ('percent', 'Percentage'),
        ],
        string='Discount Type',
    )
    discount_value = fields.Float(string='Discount Value')
    installment_ids = fields.Many2many(
        'student.fee.installment',
        'student_fee_exception_installment_rel',
        'exception_id',
        'installment_id',
        string='Affected Installments',
    )
    document = fields.Binary(string='Supporting Document', attachment=True, required=True)
    document_filename = fields.Char(string='Document Filename')
    reason = fields.Text(string='Reason')
    user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        required=True,
    )
    state = fields.Selection(
        [('done', 'Applied')],
        default='done',
        string='Status',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'student.fee.exception'
                ) or _('Exception')
        return super().create(vals_list)
