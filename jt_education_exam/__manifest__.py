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
    'name': "Exam Management",
    'sequence':3,
    'summary': "Exam Management System",
    'category': 'Student Exam',
    'version': '19.0.1.0.2',
    'depends': ['portal','website','jt_education_base','jt_education_reports','jt_education_health'],
    'data': [
        'security/ir.model.access.csv',
        'demo/demo.xml',
        'views/action_and_menu.xml',
        'views/exam_view.xml',
        'views/subject_view.xml',
        'views/result_view.xml',
        'views/grade_view.xml',
        'views/res_partner_view.xml',
        'views/result_created.xml',
        'wizard/score_summary.xml',
        'reports/score_summary_report.xml',
        'reports/result_report.xml',
    ],
    'icon': '/jt_education_exam/static/description/icon.png',
    'application': True,
    'license':'OPL-1',
}
