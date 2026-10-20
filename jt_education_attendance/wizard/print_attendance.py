# -*- coding: utf-8 -*-
##############################################################################
#
#    Jupical Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Jupical Technologies Pvt. Ltd.(<https://www.jupical.io>).
#    Author: Jupical Technologies Pvt. Ltd.(<https://www.jupical.io>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from collections import OrderedDict
from dateutil.relativedelta import relativedelta


class PrintAttendance(models.TransientModel):
    _name = 'print.attendance'
    _description = 'Attendance Report'

    start_date = fields.Date(string='From')
    end_date = fields.Date(string='To')
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
    )
    standard_id = fields.Many2one('student.standard')
    division_id = fields.Many2one('standard.division')
    class_id = fields.Many2one('student.class', string='الفصل')
    student_id = fields.Many2one(
        'res.partner',
        string='الطالب',
        domain="[('is_student', '=', True)]",
    )
    date = fields.Date(string="Today's Date", default=fields.Date.today())
    summary_report = fields.Boolean(string="Summary")

    def _get_report_filters(self, data=None):
        """Merge wizard fields with optional report data payload."""
        self.ensure_one()
        data = data or {}
        if data.get('form'):
            data = {**data, **(data.get('form') or {})}
        return {
            'start_date': fields.Date.to_date(data['start_date']) if data.get('start_date') else self.start_date,
            'end_date': fields.Date.to_date(data['end_date']) if data.get('end_date') else self.end_date,
            'company_id': data.get('company_id') or self.company_id.id,
            'standard_id': data.get('standard_id') or self.standard_id.id,
            'division_id': data.get('division_id') or self.division_id.id,
            'class_id': data.get('class_id') or self.class_id.id,
            'student_id': data.get('student_id') or self.student_id.id,
            'summary_report': data.get('summary_report', self.summary_report),
        }

    def _prepare_report_data(self):
        self.ensure_one()
        return {
            'student_id': self.student_id.id or False,
            'standard_id': self.standard_id.id or False,
            'division_id': self.division_id.id or False,
            'class_id': self.class_id.id or False,
            'company_id': self.company_id.id or False,
            'start_date': fields.Date.to_string(self.start_date) if self.start_date else False,
            'end_date': fields.Date.to_string(self.end_date) if self.end_date else False,
            'summary_report': bool(self.summary_report),
        }

    def get_report_data(self, data=None):
        """Build report datasets from attendance sheets.

        Students are often stored under branch companies while the UI company is
        the school HQ. Partner company rules then hide them and the report
        becomes empty. Load lines/students with sudo so sheet data is visible.
        """
        self.ensure_one()
        filters = self._get_report_filters(data)
        Line = self.env['attendance.line'].sudo()
        Partner = self.env['res.partner'].sudo()
        Standard = self.env['student.standard'].sudo()

        start_date = filters['start_date']
        end_date = filters['end_date']
        student_id = filters['student_id']
        summary_report = filters['summary_report']

        if not start_date or not end_date:
            return {
                'attendance_lines': Line.browse(),
                'month_name': [],
                'students': Partner.browse(),
                'class_id': self.env['student.class'],
                'student_id': Partner.browse(),
                'standards': Standard.browse(),
                'attendance_lines_new': Line.browse(),
                'all_dates': [],
                'unavailable_dates': ([], []),
            }

        att_domain = [
            ('attendance_id.date', '>=', start_date),
            ('attendance_id.date', '<=', end_date),
        ]
        if filters['company_id']:
            att_domain.append(('attendance_id.company_id', '=', filters['company_id']))
        if filters['division_id']:
            att_domain.append(('attendance_id.division_id', '=', filters['division_id']))
        if filters['standard_id']:
            att_domain.append(('attendance_id.standard_id', '=', filters['standard_id']))
        if filters['class_id'] and not summary_report:
            att_domain.append(('attendance_id.class_id', '=', filters['class_id']))
        if student_id and not summary_report:
            att_domain.append(('student_id', '=', student_id))

        attendance_lines = Line.search(att_domain, order='date, student_id')
        attendance_lines_new = attendance_lines

        if student_id and not summary_report:
            students = Partner.browse(student_id)
        else:
            students = attendance_lines.mapped('student_id')
            if not students:
                student_domain = [('is_student', '=', True)]
                if filters['division_id']:
                    student_domain.append(('div', '=', filters['division_id']))
                if filters['standard_id']:
                    student_domain.append(('standard', '=', filters['standard_id']))
                if filters['class_id']:
                    student_domain.append(('class_id', '=', filters['class_id']))
                if filters['company_id']:
                    student_domain.extend([
                        '|',
                        ('company_id', '=', False),
                        ('company_id', '=', filters['company_id']),
                    ])
                students = Partner.search(student_domain, order='name')
            else:
                students = students.sorted(key=lambda s: s.name or '')

        if summary_report:
            standards = attendance_lines_new.mapped('standard_id')
            if not standards and filters['standard_id']:
                standards = Standard.browse(filters['standard_id'])
            elif not standards:
                standards = Standard.search([])
        else:
            standards = Standard.search([])

        day_count = (end_date - start_date).days + 1
        month_name_list = OrderedDict(
            ((start_date + timedelta(days=_)).strftime(r"%B-%Y"), None) for _ in range(day_count)
        ).keys()
        all_dates = self.get_all_date(start_date, end_date)
        return {
            'attendance_lines': attendance_lines,
            'month_name': list(month_name_list),
            'students': students,
            'class_id': self.env['student.class'].sudo().browse(filters['class_id']) if filters['class_id'] else self.env['student.class'],
            'student_id': students[:1] if student_id else self.env['res.partner'],
            'standards': standards,
            'attendance_lines_new': attendance_lines_new,
            'all_dates': all_dates,
            'unavailable_dates': self._get_unavailable_dates_for(start_date, end_date),
            'start_date': start_date,
            'end_date': end_date,
            'company_name': self.env['res.company'].sudo().browse(filters['company_id']).name if filters['company_id'] else (self.env.company.name or ''),
            'standard_name': self.env['student.standard'].sudo().browse(filters['standard_id']).name if filters['standard_id'] else '',
            'division_name': self.env['standard.division'].sudo().browse(filters['division_id']).name if filters['division_id'] else '',
            'class_name': self.env['student.class'].sudo().browse(filters['class_id']).name if filters['class_id'] else '',
        }

    def get_all_date(self, start_date, end_date):
        date_list = []
        current = start_date
        while current <= end_date:
            date_list.append(current)
            current += timedelta(days=1)
        return date_list

    def _get_unavailable_dates_for(self, start_date, end_date):
        date_list_str = []
        day_list = []
        if not start_date or not end_date or 'custom.calendar' not in self.env:
            return date_list_str, day_list
        calendar = self.env['custom.calendar'].search([
            ('start_date', '<=', start_date),
            ('end_date', '>=', start_date),
        ], limit=1)
        for off_day in calendar.weekoff_ids:
            day_list.append(off_day.name[:3])
        for holiday in calendar.holiday_ids:
            if holiday.h_start_date >= start_date and holiday.h_end_date <= end_date:
                if holiday.h_start_date == holiday.h_end_date:
                    date_list_str.append(holiday.h_start_date)
                else:
                    h_start = holiday.h_start_date
                    while h_start <= holiday.h_end_date:
                        date_list_str.append(h_start)
                        h_start += timedelta(days=1)
        return date_list_str, day_list

    def _get_unavailable_dates(self):
        return self._get_unavailable_dates_for(self.start_date, self.end_date)

    def get_attendance_summary_data(self):
        self.ensure_one()
        self.flush_recordset()
        return self.env.ref('jt_education_attendance.action_summary_attendance_report').with_context(
            discard_logo_check=True,
        ).report_action(self, data=self._prepare_report_data(), config=False)

    def generate_attendance_report(self):
        self.ensure_one()
        self.flush_recordset()
        return self.env.ref('jt_education_attendance.action_attendance_report').with_context(
            discard_logo_check=True,
        ).report_action(self, data=self._prepare_report_data(), config=False)
