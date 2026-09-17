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
    'name': "Assignment Management",
    'sequence': 9,
    'version': '19.0.1.0.2',
    'summary': "Assignment Management System",
    'category': 'Student Assignment',
    'depends': ['portal','website','jt_education_base','jt_education_exam','base_automation','jt_education_library'],
    'data': [
        'security/ir.model.access.csv',
        'demo/assignment_type_demo.xml',
        'views/action_and_menu.xml',
        'views/assignment_submission_view.xml',
        'views/assignment_type_view.xml',
        'views/assignment_view.xml',
        'views/student_view.xml',
    ],
    'icon': '/jt_education_assignment/static/description/icon.png',
    'application': True,
    'license':'OPL-1',
}
