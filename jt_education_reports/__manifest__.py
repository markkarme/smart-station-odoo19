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
################################################################################
{
    'name': "Reports Printing",
    'sequence':2,
    'summary': "Manage the students icards",
    'category': 'Reports Print',
    'version': '19.0.1.0.0',
    'depends': ['jt_education_base','stock','sale','account'],
    'data': [
        # 'demo/demo.xml',
        'views/res_company.xml',
        'reports/emp_classic_icard.xml',
        'reports/emp_classic_back.xml',
        'reports/light_icard_report_front.xml',
        'reports/light_icard_report_back.xml',
        'reports/stylish_icard_report_front.xml',
        'reports/stylish_icard_report_back.xml',
        'reports/green_icard_repot_frontend.xml',
        'reports/green_icard_backend.xml',
        'reports/purple_icard_frontend.xml',
        'reports/purple_icard_backend.xml',
        'reports/red_icard_front.xml',
        'reports/red_icard_back.xml',
        'reports/blue_front_icard.xml',
        'reports/blue_back_icard.xml',
        'reports/square_id_front.xml',
        'reports/square_id_back.xml',
        'reports/white_icard_frontend.xml',
        'reports/white_icard_backend.xml',
        'reports/multi_icard_frontend.xml',
        'reports/multi_icard_backend.xml',
        'reports/navy_icard_frontend.xml',
        'reports/navy_icard_backend.xml',
        'reports/yellow_icard_frontend.xml',
        'reports/yellow_icard_backend.xml',
        'reports/leaving_certificate.xml',
        'reports/experiencecertificate_template.xml',
        'reports/experiencecertificate_landscape_template.xml',
        'reports/black_experiencecertificate_landscape.xml',
        # 'reports/invoice_report_ext.xml',
        # 'reports/payment_receipt_ext.xml',
        # 'reports/sale_order_ext.xml',
        # 'reports/picking_report_ext.xml',
        # 'reports/delivery_report_ext.xml'


    ],
    'icon': '/jt_education_reports/static/description/icon.png',
    'application': True,
    'license':'OPL-1',
}
