# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    violation_ids = fields.One2many('student.violation', 'student_id', string='المخالفات')
    violation_count = fields.Integer(compute='_compute_violation_count', string='المخالفات')
    case_study_ids = fields.One2many('student.case.study', 'student_id', string='دراسات الحالة')
    case_study_count = fields.Integer(compute='_compute_case_study_count', string='دراسات الحالة')

    def _compute_violation_count(self):
        Violation = self.env['student.violation']
        for partner in self:
            partner.violation_count = Violation.search_count([('student_id', '=', partner.id)])

    def _compute_case_study_count(self):
        CaseStudy = self.env['student.case.study']
        for partner in self:
            partner.case_study_count = CaseStudy.search_count([('student_id', '=', partner.id)])

    def action_view_student_violations(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'jt_student_violations.action_student_violation'
        )
        action['domain'] = [('student_id', '=', self.id)]
        action['context'] = {
            'default_student_id': self.id,
            'default_class_id': self.class_id.id,
            'default_div_id': self.div.id,
            'default_company_id': self.company_id.id or self.env.company.id,
        }
        return action

    def action_view_student_case_studies(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'jt_student_violations.action_student_case_study'
        )
        action['domain'] = [('student_id', '=', self.id)]
        action['context'] = {
            'default_student_id': self.id,
            'default_name': self.name,
            'default_class_id': self.class_id.id,
            'default_div_id': self.div.id,
            'default_company_id': self.company_id.id or self.env.company.id,
        }
        return action
