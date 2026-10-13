# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StudentViolation(models.Model):
    _name = 'student.violation'
    _description = 'مخالفة الطالب'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        index=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    student_id = fields.Many2one(
        'res.partner',
        string='الطالب',
        required=True,
        domain="[('is_student', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
        ondelete='cascade',
    )
    stud_id = fields.Char(related='student_id.stud_id', string='رقم الطالب', store=True, readonly=True)
    father_name = fields.Char(related='student_id.father_name', string='اسم الأب', readonly=True)
    surname = fields.Char(related='student_id.surname', string='اللقب', readonly=True)
    standard_id = fields.Many2one(
        related='student_id.standard',
        string='الصف',
        store=True,
        readonly=True,
    )
    class_id = fields.Many2one(
        'student.class',
        string='الفصل',
        tracking=True,
    )
    div_id = fields.Many2one(
        'standard.division',
        string='الشعبة',
        tracking=True,
    )
    date = fields.Date(
        string='التاريخ',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    violation_type = fields.Selection(
        selection=[
            ('fighting', 'المشاجرة أو إيذاء زميله'),
            ('bullying', 'التنمر والألفاظ غير اللائقة'),
            ('filming', 'تصوير أو نشر مقاطع من داخل المحطة'),
            ('uniform', 'عدم الالتزام بالزي المدرسي'),
            ('late_morning', 'التأخر الصباحي عن موعد المدرسة'),
            ('no_books', 'عدم إحضار الكتب والأدوات المدرسية'),
            ('mobile', 'عدم تسليم الموبايل للمشرف المختص'),
            ('disrespect_staff', 'إساءة الأدب مع هيئة التدريس'),
            ('theft', 'السرقة'),
            ('smoking', 'التدخين'),
            ('drugs_weapons', 'حيازة المخدرات والسلاح'),
            ('truancy', 'الهروب من المدرسة'),
            ('cheating', 'الغش في الاختبارات'),
            ('vandalism', 'تخريب الممتلكات'),
            ('class_permission', 'الدخول أو الخروج من الفصل بدون استئذان'),
            ('bus_misbehavior', 'السلوكيات الخاطئة داخل الباص'),
        ],
        string='المخالفات',
        required=True,
        tracking=True,
    )
    action_taken = fields.Selection(
        selection=[
            ('verbal_warning', 'تنبيه شفوي'),
            ('warning', 'إنذار'),
            ('expulsion', 'فصل'),
            ('call_guardian', 'استدعاء ولي الأمر'),
            ('caution', 'تحذير'),
            ('written_pledge', 'تعهد كتابي'),
            ('lower_behavior_grades', 'خفض درجات السلوك'),
            ('deny_entry_same_day', 'عدم دخول المدرسة في نفس اليوم'),
            ('bar_activities', 'عدم الاشتراك في الأنشطة'),
            ('suspend_pending', 'إيقاف الطالب لحين اتخاذ إجراء مناسب'),
            ('suspend_15_days', 'فصل لمدة 15 يوم'),
            ('lower_teacher_grades', 'خفض درجات من جانب المعلم'),
            ('case_study', 'دراسة حالة'),
        ],
        string='الإجراء المتخذ مع الطالب',
        tracking=True,
    )
    notes = fields.Text(string='الملاحظات')
    description = fields.Text(string='وصف المشكلة')

    @api.depends('student_id', 'violation_type', 'date')
    def _compute_display_name(self):
        violation_labels = dict(self._fields['violation_type'].selection)
        for rec in self:
            parts = []
            if rec.student_id:
                parts.append(rec.student_id.name)
            if rec.violation_type:
                parts.append(violation_labels.get(rec.violation_type, rec.violation_type))
            if rec.date:
                parts.append(str(rec.date))
            rec.display_name = ' - '.join(parts) if parts else _('مخالفة الطالب')

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.class_id = self.student_id.class_id
            self.div_id = self.student_id.div
            if self.student_id.company_id:
                self.company_id = self.student_id.company_id
        else:
            self.class_id = False
            self.div_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)
