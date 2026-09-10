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

class EducationPortal(CustomerPortal):
	
	@http.route(['/my/student_list'], type='http', auth="user", website=True)
	def portal_my_student_list(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):

		values = {}
		student_links =[]
		student_result ={}

		contact_obj = request.env['res.partner']

		parent_id = request.env.user.partner_id.id
		students = contact_obj.sudo().search([('parentsid','=',parent_id)])

		#loop for Creating URL With ID. 
		for stud in students:
			student_detail_url = '/my/student_details/'+str(stud.id)
			student_links.append(student_detail_url) 

		
		#loop for combining two list in one dictionary and then send that combined dictionary to template where list is being displayed.    
		for link_info,student_info in zip(student_links,students):
			student_result.update({link_info:student_info})


		values.update({
			'student_list':student_result,
		})
		
		return request.render("jt_education_portal.portal_student_list", values)
	
	
	@http.route([
		'/my/student_profile',
		'/my/student_profile/<int:student_data>'
		], type='http', auth="user", website=True)
	def portal_my_student_profilee(self, page=0, student_data = None,date_begin=None, date_end=None, sortby=None, **kw):

		values = {}

		partner = request.env.user.partner_id

		student_obj = request.env['res.partner']

		
		if student_data:
			student_id = student_obj.sudo().browse(student_data)
		else:
			student_id = request.env.user.partner_id


		values.update({
			'student':student_id,
			'partner':partner,
		})
		
		return request.render("jt_education_portal.portal_student_profile", values)


	@http.route(['/my/student_details/<int:student_data>'], type='http', auth="user", website=True) 
	def portal_my_student_detail_list(self, student_data,page=1, date_begin=None, date_end=None, sortby=None, **kw):

		values = {}
		student_exam_links =[]
		student_exam_result ={}
		student_result_links =[]
		student_result_result ={}

		exam_obj = request.env['student.timetable'].sudo().search([])
		result_obj = request.env['student.result'].sudo().search([])
		
		for ex in exam_obj.student_ids:
			for rec in ex.student_ids.ids:
				if ex == stud:
					student_exam_detail_url = '/my/exam/page/'+str(stud)
					student_exam_links.append(student_exam_detail_url)

		for stud in result_obj:
		  for rec in stud.student_id:
			  if rec.id == stud:
				  student_result_detail_url = '/my/result/page/'+str(stud.id)
				  student_result_links.append(student_result_detail_url)


		for link_exam_info,student_exam_info in zip(student_exam_links,exam_obj):
			student_exam_result.update({link_exam_info:student_exam_info})

		for link_result_info,student_result_info in zip(student_result_links,result_obj):
		  student_result_result.update({link_result_info:student_result_info})
		
		values.update({
			'profile' : "/my/student_profile/"+str(student_data),
			'issue_book' : "/my/issue_books_list/"+str(student_data),
			'membership' : "/my/membership_list/"+str(student_data),
			'exams' : "/my/exam_list/"+str(student_data),
			'result' : "/my/result_list/"+str(student_data),
			'assignment' : "/my/assignment_list/"+str(student_data),
			'submission' : "/my/submission_list/"+str(student_data),
			'events' : "/my/event_list/"+str(student_data),
			'timetable' : "/my/timetable_list/"+str(student_data),
			'fees' : "/my/fees_list/"+str(student_data),
			'holidays' : "/my/holidays_list/"+str(student_data),
			'transport' : "/my/transport_list/"+str(student_data),
			'hostel_registration' : "/my/hostel_registration_list/"+str(student_data),
			'hostel_complaint' : "/my/hostel_complaint_list/"+str(student_data),
			'hostel_meeting' : "/my/hostel_meeting_list/"+str(student_data),
			'student_list_exam':student_result_links,
			'student_list_result':student_result_result

		})

		return request.render("jt_education_portal.portal_student_details_list", values)


class ParentPortalController(http.Controller):

    @http.route(['/my/student_list'], type='http', auth="user", website=True)
    def parent_student_list_view(self, **kwargs):
        parent = request.env.user.partner_id
        students = parent.student_ids.sudo()  # Using One2many field
        values = {
            'students': students,
        }
        return request.render("jt_education_portal.portal_parent_student_list", values)