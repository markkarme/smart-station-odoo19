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
    'name': "Portal For Education",
    'sequence': 10,
    'version': '19.0.1.0.0',
    'category': 'Portal Module',
    'summary': "Manage the Portal users for all education modules",
    'depends': ['portal','website','jt_education_base','jt_education_event','jt_education_exam','jt_education_fees','jt_education_library','jt_education_assignment','jt_education_timetable'],
    'data': [
        'security/ir.model.access.csv',
        'views/portal_view.xml',
        'views/parent_portal_view.xml',
    ],
    'application': True,
    'license':'OPL-1',
}