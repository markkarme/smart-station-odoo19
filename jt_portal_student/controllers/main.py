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
from odoo import fields, http, _
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request
from datetime import datetime
from odoo.exceptions import AccessError, MissingError
from odoo.tools.misc import format_date
import base64

class StudentDetailsPortal(http.Controller):

	@http.route(['/my/student_details', '/my/student_details/<int:student_data>'], type='http', auth="user", website=True)
	def portal_my_student_details(self, student_data=None, **kw):
		if student_data:
			student = request.env['res.partner'].sudo().browse(student_data)
		else:
			student = request.env.user.partner_id

		student_details = {
			'name': f"{student.name} {student.surname}",
			'email': student.email,
			'phone': student.mobile,
			'standard': student.standard.name,
			'division': student.div.name,
			'curr_year': student.curr_year.name,
			'birthdate': student.birthdate.strftime('%Y-%m-%d') if student.birthdate else 'N/A',
			'state': dict(student._fields['state'].selection).get(student.state, 'N/A'),
			'date':student.application_submission_date
		}

		return request.render("jt_portal_student.portal_student_details", {
			'student_details': student_details,
		})


	@http.route(['/my/student_details/preview_application_form', '/my/student_details/<int:student_data>/preview_application_form'], type='http', auth="user", website=True)
	def portal_my_student_form_preview(self, student_data=None, **kw):
		if student_data:
			student_info = request.env['res.partner'].sudo().browse(student_data)
		else:
			student_info = request.env.user.partner_id

		image_1920 = student_info.image_1920
		if isinstance(image_1920, bytes):
			image_1920 = image_1920.decode('utf-8')
		signature = student_info.signature
		if isinstance(signature, bytes):
			signature = signature.decode('utf-8')
		marksheet = student_info.marksheet_attachment_pdf
		adhar = student_info.adhar_attachment_pdf

		student_info_details = {
			'name' : student_info.name,
			'surname' : student_info.surname,
			'father_name' : student_info.father_name,
			'mother_name' : student_info.mother_name,
			'street' : student_info.street,
			'street2' : student_info.street2,
			'country_id' : student_info.country_id.name if student_info.country_id else '',
			'state_id' : student_info.state_id.name if student_info.state_id else '',
			'city' : student_info.city,
			'zip_code' : student_info.zip,
			'mobile' : student_info.mobile,
			'email' : student_info.email,
			'caste' : student_info.caste,
			'subcaste' : student_info.subcaste,
			'nationality' : student_info.nationality,
			'religion' : student_info.religion,
			'birthPlace' : student_info.birthPlace,
			'mother_tonque' : student_info.mother_tonque,
			'village' : student_info.village.name,
			'province' : student_info.province.name,
			'district_id' : student_info.district_id.name,
			'curr_year' : student_info.curr_year.name,	
			'image_1920' : image_1920 or None,	
			'signature' : signature or None,
			'marksheet_attachment_pdf': base64.b64encode(marksheet).decode('utf-8') if marksheet else None,
			'marksheet_attachment_pdf_file': student_info.marksheet_attachment_pdf_file if marksheet else False,
			'adhar_attachment_pdf': base64.b64encode(adhar).decode('utf-8') if adhar else None,
			'adhar_attachment_pdf_file': student_info.adhar_attachment_pdf_file if adhar else False,
			'state': dict(student_info._fields['state'].selection).get(student_info.state, 'N/A'),

		}

		return request.render("jt_portal_student.admission_form_preview_page", student_info_details)