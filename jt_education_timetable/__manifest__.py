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
    'name': "Student Timetable",
    'sequence':5,
    'version': '19.0.1.0.2',
    'summary': "Manage Students Timetable",
    'category': 'Timetable Management',
    'depends': ['jt_education_base','jt_education_exam'],
    'data': [
        'security/ir.model.access.csv',
        'security/timetable_security.xml',
        # 'demo/demo.xml',
        'views/faculty_timetable.xml',
        'views/timetable_view.xml',
        'views/period_view.xml',
        'views/action_and_menu.xml',
    ],
    'icon': '/jt_education_timetable/static/description/icon.png',
    'application': True,
    'license':'OPL-1',
}
