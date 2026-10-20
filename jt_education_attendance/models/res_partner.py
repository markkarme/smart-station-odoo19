# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    attendance_line_ids = fields.One2many(
        'attendance.line',
        'student_id',
        string='سجل الحضور',
    )
    attendance_line_count = fields.Integer(
        string='عدد سجلات الحضور',
        compute='_compute_attendance_line_count',
    )

    def _compute_attendance_line_count(self):
        AttendanceLine = self.env['attendance.line']
        for partner in self:
            partner.attendance_line_count = AttendanceLine.search_count([
                ('student_id', '=', partner.id),
            ])

    def action_view_student_attendance(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'jt_education_attendance.action_student_attendance_history'
        )
        action['domain'] = [('student_id', '=', self.id)]
        action['context'] = {
            'default_student_id': self.id,
            'create': False,
        }
        action['name'] = _('سجل الحضور - %s') % (self.display_name or self.name)
        return action
