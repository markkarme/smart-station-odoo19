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
{
    'name': "Attendance Management",
    'sequence':6,
    'version': '19.0.1.0.1',
    'summary': "Manage the Attendance of students",
    'category': 'Student Attendance',
    'depends': ['jt_education_base', 'jt_education_exam'],
    'data': [

        'security/ir.model.access.csv',
        'views/attendance_view.xml',
        'reports/report_attendance.xml',
        'reports/education_summary_report_view.xml',
        'reports/daily_attendance.xml',
        'wizard/print_attendance.xml',
        'views/attendance_summary_view.xml',
        'views/absent_student_mail.xml',
    ],
    'icon': '/jt_education_attendance/static/description/icon.png',
    'application': True,
   'license':'OPL-1',
}
