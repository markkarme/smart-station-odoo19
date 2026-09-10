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


class StudentComplaints(models.Model):

	_name = 'student.complaints'
	_description = "Manage Hostel Students Complaints"
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			   ]


	name = fields.Char("Complaint")
	student_id = fields.Many2one('res.partner', string="Student", domain=[('is_student', '=', True)])
	state = fields.Selection([
		('new', 'New'),
		('assigned', 'Assigned'),
		('in_progress', 'In Progress'),
		('resolved', 'Resolved'),
		('cancel', 'Cancelled')
	], default="new", string="Status", readonly=True,tracking=True)
	date = fields.Date(string="Date", default=fields.Date.today())
	description = fields.Text(string="Description")
	cancel_reason = fields.Text(string="Reason for Cancellation")
	closing_date = fields.Date(string="Closing Date")
	assign_id = fields.Many2one('res.users', store=True, string='Assigned to',domain=[('is_student', '=', False)],tracking=True)

	def complaint_assigned(self):
		self.ensure_one()
		self.state = 'assigned'

	def complaint_in_progress(self):
		self.ensure_one()
		self.state = 'in_progress'

	def complaint_resolved(self):
		self.ensure_one()
		self.state = 'resolved'

	def complaint_cancelled(self):
		self.ensure_one()
		self.state = 'cancel'
		action = self.env["ir.actions.actions"]._for_xml_id('jt_education_hostel.action_cancel_reason_wizard')
		return action

		