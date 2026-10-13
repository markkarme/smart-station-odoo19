# -*- coding: utf-8 -*-
from odoo import fields, models


class StudentCaseStudyFamily(models.Model):
    _name = 'student.case.study.family'
    _description = 'فرد من التكوين الأسري'
    _order = 'sequence, id'

    case_study_id = fields.Many2one(
        'student.case.study',
        string='دراسة الحالة',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='case_study_id.company_id',
        store=True,
        readonly=True,
        string='الشركة',
    )
    sequence = fields.Integer(default=10)
    relation_type = fields.Selection(
        selection=[
            ('father', 'الأب'),
            ('mother', 'الأم'),
            ('other', 'آخرون'),
        ],
        string='الصلة',
        required=True,
    )
    name = fields.Char(string='الاسم')
    age = fields.Integer(string='العمر')
    education = fields.Char(string='التعليم - المؤهل الدراسي')
    job = fields.Char(string='الوظيفة')
    economic_level = fields.Selection(
        selection=[
            ('high', 'عالي'),
            ('medium', 'متوسط'),
            ('low', 'منخفض'),
        ],
        string='المستوى الاقتصادي',
    )

    def get_selection_label(self, field_name):
        self.ensure_one()
        value = self[field_name]
        if not value:
            return ''
        return dict(self._fields[field_name]._description_selection(self.env)).get(value, value)
