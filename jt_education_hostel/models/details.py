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


class HostelDetails(models.TransientModel):

	_name = 'hostel.details'
	_description = "Hostel Details"
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			   ]
	_rec_name = 'curr_year_id'

	hostel_data = fields.Html(string="Hostel Data")
	curr_year_id = fields.Many2one('year.year', string='Academic Year',store=True)
	link = fields.Char(string="Link")


	@api.onchange('curr_year_id')
	def _onchange_curr_year_id(self):
		if self.curr_year_id:
			registration_obj = self.env['hostel.registration'].search([('curr_year_id','=',self.curr_year_id.name),('state','=','active')])
			if registration_obj:
				values = ""
				hostel_data = self.env['hostel.building'].search([])
				hostel_detail_obj = self.env['hostel.details']
				html_data = ["<html><body>","<table class='table'>"]
				values += "".join(html_data)
				for data in hostel_data:
					values += "<thead><tr><th style='width:100%;border-bottom: none;background-color:#EEDBE4;' colspan='2'><b>" + data['name'] + "</b>"
					values += "<tr><td><b>" + "Room Name" + "</b>"
					values += "<td><b>" + "Status" + "</b>"
					for rooms in data.room_ids:
						current_students_count = len(rooms.student_ids)
	
						values += "<tr><td>" + rooms['name'] + "</td>"
						values += "<td>"
						for i in range(rooms.capacity):
							if i < current_students_count:
								values += "<div style='display:inline-block;width:20px;height:20px;margin:2px;background-color:red;border:1px solid #000;'><img src='jt_education_hostel/static/src/image/reserved.png' style='width:100%;height:100%;'></div>"
							else:
								values +=f"""
								<div style='display:inline-block;width:20px;height:20px;margin:2px;border:1px solid #000;'>
									<a href="/web#action=jt_education_hostel.action_hostel_registration&amp;view_type=form&amp;model=hostel.registration&amp;context={{'default_building_id':'{data.id}','default_room_id':'{rooms.id}'}}" target='current'>
										<img src='/jt_education_hostel/static/src/image/free.png' style='width:20px;height:20px;' alt='Free Room'>
										</img>
									</a>
								</div>
								"""

						values += "</td></tr>"
						# if current_students_count >= rooms.capacity:
						# 	values += "<td><div class='alert alert-info'>Reserved</div></td>"
						# else:
						# 	space = rooms.capacity - current_students_count
						# 	values += "<td><div class='alert alert-success'>" + "Free(" + str(space) +")" + "</div></td>"
				values += "</tbody></table></body></html>"
				self.write({'hostel_data':values})
			else:
				values = ""
				hostel_data = self.env['hostel.building'].search([])
				hostel_detail_obj = self.env['hostel.details']
				html_data = ["<html><body>","<table class='table'>"]
				values += "".join(html_data)
				for data in hostel_data:
					values += "<thead><tr><th style='width:100%;border-bottom: none;background-color:#EEDBE4;' colspan='2'><b>" + data['name'] + "</b></th></tr></thead>"
					values += "<tbody><tr><td><b>Room Name</b></td><td><b>Status</b></td></tr>"
					# values += "<td><b>" + "Status" + "</b>"
					for rooms in data.room_ids:
						values += "<tr><td>" + rooms['name'] + "</td>"
						values += "<td>"
						# values += "<td><div class='alert alert-success'>" + "Free" + "</div></td>"
						for i in range(rooms.capacity):
							values += f"""
								<div style='display:inline-block;width:20px;height:20px;margin:2px;border:1px solid #000;'>
									<a href="/web#action=jt_education_hostel.action_hostel_registration&amp;view_type=form&amp;model=hostel.registration&amp;context={{'default_building_id':'{data.id}','default_room_id':'{rooms.id}'}}" target='current'>
										<img src='/jt_education_hostel/static/src/image/free.png' style='width:20px;height:20px;' alt='Free Room'>
										</img>
									</a>
								</div>
								"""
						values += "</td></tr>"
						
				values += "</tbody></table></body></html>"
				self.write({'hostel_data':values})

	# def open_room_allocation_form_view(self):
	# 	action = self.env.ref('jt_education_hostel.action_hostel_details').read()[0]
	# 	return action