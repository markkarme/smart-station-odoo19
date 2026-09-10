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
from odoo import models, fields, api, exceptions, _
from datetime import timedelta
from odoo.exceptions import ValidationError,UserError

class SubjectLine(models.Model):
	_name = 'subject.line'
	_description = 'Subject Line'
	_rec_name = 'subject_id'

	subject_id = fields.Many2one(
		'student.subject', string='Subject', help="Select Subjects")
	date = fields.Date(string='Date')
	day = fields.Selection([('sunday', 'Sunday'), ('monday', 'Monday'),
							  ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),('thursday', 'Thursday'),
							  ('friday', 'Friday'), ('saturday', 'Saturday')], default='monday')
	time_from = fields.Float(related='exam_id.time_from',string='Time From', help="Start time")
	time_to = fields.Float(related='exam_id.time_to',string='Time To', help="Finish time")
	mark = fields.Integer(string='Mark',help="Total Marks of Subject")
	exam_id = fields.Many2one('student.exam', string='Exam')

class StudentSubject(models.Model):
	_name = 'student.subject'
	_description = 'Student Subject'
   
	_code_uniq = models.Constraint(
		'UNIQUE(code)',
		'Another Subject already exists with this code!',
	)

	name = fields.Char(string='Name', help="Name of the Subject")
	code = fields.Char(string="Code", help="Enter the Subject Code")
	subject_category_id = fields.Many2one('subject.category', string='Subject Category')
	mark = fields.Float('Marks')
	pass_mark = fields.Float('Passing Marks')


	@api.depends('name', 'code')
	def _compute_display_name(self):
		for rec in self:
			rec.display_name = '%s - %s' % (rec.code or '', rec.name or '')

   

class StudentExam(models.Model):
	_name = 'student.exam'
	_description = 'Generate Student Exams'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]

	@api.depends('name', 'start_date', 'standard.name', 'division.name')
	def _compute_display_name(self):
		for rec in self:
			rec.display_name = '%s - %s(%s-%s)' % (
				rec.name or '',
				rec.start_date or '',
				rec.standard.name or '',
				rec.division.name or '',
			)

	@api.constrains('start_date', 'end_date')
	def check_dates(self):
		for rec in self:
			if rec.start_date > rec.end_date:
				raise ValidationError("Start date must be Greater to end date")
	

	@api.constrains('standard', 'division', 'start_date', 'end_date')
	def _check_duplicate_exam(self):
		for rec in self:
			existing_exam = self.env['student.exam'].search([
				('standard', '=', rec.standard.id),
				('division', '=', rec.division.id),
				('start_date', '=', rec.start_date),
				('end_date', '=', rec.end_date),
				('id', '!=', rec.id)
			])
			if existing_exam:
				raise ValidationError("Exam with similar standard and division already exists")			

	student_ids = fields.Many2many(
		'res.partner', domain=[('is_student', '=', True)])
	name = fields.Char(string='Name')
	start_date = fields.Date('Start Date')
	end_date = fields.Date('End Date')
	subject_line = fields.One2many(
		'subject.line', 'exam_id', string='Subjects')
	standard = fields.Many2one(
		'student.standard', string="Standard")
	division = fields.Many2one(
		'standard.division', string="Division")
	curr_year = fields.Many2one('year.year', string='Year')
	state = fields.Selection([('draft', 'Draft'), ('ongoing', 'On Going'),
							  ('close', 'Closed'), ('cancel', 'Canceled')], default='draft')

	time_from = fields.Float(string='Time From', help="Start time")
	time_to = fields.Float(string='Time To', help="Finish time")
	is_annual = fields.Boolean('Is Annual ?')
	
	
	# @api.onchange('student_ids')
	# def manage_student_results(self):
	# 	print("helloo_________")
	# 	for exam in self:
	# 		for student in exam.student_ids:
				
	# 			result = self.env['student.result'].search([
	# 				('student_id', '=', student.id),
	# 				('exam_id', '=', exam.id)
	# 			], limit=1, order='id desc')  
				
	# 			if result:
	# 				student.student_result = result.percentage
	# 			else:
	# 				student.student_result = 0.0


	@api.onchange('start_date', 'end_date')
	def _onchange_dates(self):

		if self.start_date and self.end_date:
			date_diff = (self.end_date - self.start_date).days
			self.subject_line = [(5, 0, 0)]
			sub_line_obj = self.env['subject.line']
			exam_date = self.start_date
			line_datas = []
			count = 1
			for i in range(date_diff+1):
				day_name = exam_date.strftime("%A")
				day_name = day_name.lower()
				line_info = {
					'exam_id': self.id,
					'date': exam_date,
					'day':day_name,
				}
				
				exam_date = exam_date + timedelta(days=count)

				
				line_datas.append((0,0,line_info))
			self.subject_line = line_datas
				
	def close_exam(self):
		self.state = 'close'

	def cancel_exam(self):
		self.state = 'cancel'

	def ongoing_exam(self):
		self.state = 'ongoing'


class ResUsers(models.Model):
	_inherit = 'res.users'

	is_student = fields.Boolean(string='Is Student', compute='_compute_is_student_and_is_parent')
	is_parent = fields.Boolean(string='Is Parent', compute='_compute_is_student_and_is_parent')

	@api.depends('partner_id')
	def _compute_is_student_and_is_parent(self):
		for user in self:
			if user.partner_id:
				user.is_student = user.partner_id.is_student
				user.is_parent = user.partner_id.is_parent
			else:
				user.is_student = False
				user.is_parent = False 
