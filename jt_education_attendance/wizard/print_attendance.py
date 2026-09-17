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
# from dateutil import relativedelta
from datetime import datetime, timedelta
from collections import OrderedDict
import calendar
from dateutil.relativedelta import relativedelta


class PrintAttendance(models.TransientModel):
    _name = 'print.attendance'
    _description = 'Attendance Report'

    start_date = fields.Date(string='From')
    end_date = fields.Date(string='To')
    standard_id = fields.Many2one('student.standard')
    division_id = fields.Many2one('standard.division')
    student_id = fields.Many2one('res.partner', string="Students", domain=[('is_student','=', True)])
    date = fields.Date(string="Today's Date", default=fields.Date.today())
    faculty_id = fields.Many2one('res.partner',string="Faculties",domain=[('is_faculty', '=', True)])
    summary_report = fields.Boolean(string="Summary")


    def get_report_data(self):
        domain =[]
        if self.division_id and self.standard_id :
            domain = [('is_student', '=', True), ('div','=',self.division_id.id), ('standard','=',self.standard_id.id)]
        elif self.division_id and not self.standard_id :
            domain = [('is_student', '=', True),('div','=',self.division_id.id)]
        elif not self.division_id and self.standard_id:
            domain = [('is_student', '=', True),('standard','=',self.standard_id.id)]
        else:
            domain = [('is_student', '=', True)]
        students = self.env['res.partner'].search(domain)
        faculties = self.faculty_id
        attendance_lines = self.env['attendance.line'].search([('student_id','in',students.ids),('attendance_id.date','>=',self.start_date),('attendance_id.date','<',self.end_date)])
        attendance_lines_new = self.env['attendance.line'].search([('student_id','in',students.ids),('attendance_id.date','>=',self.start_date),('attendance_id.date','<=',self.end_date)])
        standards = self.env['student.standard'].search([])
        month_name_list = OrderedDict(((self.start_date + timedelta(_)).strftime(r"%B-%Y"), None) for _ in range((self.end_date - self.start_date).days)).keys()       
        data = {'attendance_lines':attendance_lines,
                'month_name':list(month_name_list),
                'students': students,
                'faculties':faculties,
                'standards':standards,
                'attendance_lines_new':attendance_lines_new,
                }
        return data


    def get_all_date(self,start_date,end_date):
        date_list = []
        if start_date == end_date:
            date_list.append(start_date)
        else:
            while start_date != end_date:
                date_list.append(start_date)
                start_date += timedelta(days=1)
        return date_list


    def _get_unavailable_dates(self):
        date_list_str = []
        day_list = []
        if 'custom.calendar' not in self.env:
            return date_list_str, day_list
        calendar = self.env['custom.calendar'].search([
            ('start_date', '<=', self.start_date),
            ('end_date', '>=', self.start_date),
        ], limit=1)
        for off_day in calendar.weekoff_ids:
            day_list.append(off_day.name[:3])
        for holiday in calendar.holiday_ids:
            if holiday.h_start_date >= self.start_date and holiday.h_end_date <= self.end_date:
                if holiday.h_start_date == holiday.h_end_date:
                    date_list_str.append(holiday.h_start_date)
                else:
                    while holiday.h_start_date <= holiday.h_end_date:
                        date_list_str.append(holiday.h_start_date)
                        holiday.h_start_date += timedelta(days=1)
        return date_list_str, day_list

    def get_attendance_summary_data(self):
        self.ensure_one()
        return self.env.ref('jt_education_attendance.action_summary_attendance_report').report_action(self)

    def generate_attendance_report(self):
        self.ensure_one()
        return self.env.ref('jt_education_attendance.action_attendance_report').report_action(self)
