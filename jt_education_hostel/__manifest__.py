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
    'name': "Hostel Management",
    'version': '19.0.1.0.1',
    'category': 'Hostel Management',
    'summary': "Hostel Management",
    'depends': ['jt_education_base','sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/hostel_security.xml',
        'views/hostel_view.xml',
        'views/building_view.xml',
        'views/room_view.xml',
        'views/details_view.xml',
        'views/complaint_view.xml',
        'views/meeting_view.xml',
        'wizard/cancel_reason.xml',
       
    ],
    'icon': '/jt_education_hostel/static/description/icon.png',
    'application': True,
    'license': 'OPL-1',

}
