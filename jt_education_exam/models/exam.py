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
import base64
import os

from markupsafe import Markup
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError, UserError
from odoo.modules.module import get_module_path
from datetime import timedelta

DAY_LABELS_AR = {
	'sunday': 'الأحد',
	'monday': 'الإثنين',
	'tuesday': 'الثلاثاء',
	'wednesday': 'الأربعاء',
	'thursday': 'الخميس',
	'friday': 'الجمعة',
	'saturday': 'السبت',
}

class SubjectLine(models.Model):
	_name = 'subject.line'
	_description = 'Subject Line'
	_rec_name = 'subject_id'
	_order = 'sequence, id'

	sequence = fields.Integer(string='Sequence', default=10)
	subject_id = fields.Many2one(
		'student.subject', string='Subject', help="Select Subjects")
	date = fields.Date(string='Date')
	day = fields.Selection([('sunday', 'Sunday'), ('monday', 'Monday'),
							  ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),('thursday', 'Thursday'),
							  ('friday', 'Friday'), ('saturday', 'Saturday')], default='monday')
	time_from = fields.Float(string='Time From', help="Start time")
	time_to = fields.Float(string='Time To', help="Finish time")
	mark = fields.Integer(string='Mark',help="Total Marks of Subject")
	exam_id = fields.Many2one('student.exam', string='Exam')
	exam_start_date = fields.Date(related='exam_id.start_date', string='Exam Start Date')
	exam_end_date = fields.Date(related='exam_id.end_date', string='Exam End Date')

	@api.onchange('exam_id')
	def _onchange_exam_id(self):
		for line in self:
			if line.exam_id:
				if not line.time_from:
					line.time_from = line.exam_id.time_from
				if not line.time_to:
					line.time_to = line.exam_id.time_to

	@api.onchange('date')
	def _onchange_date(self):
		for line in self:
			if line.date:
				line.day = line.date.strftime('%A').lower()

	@api.constrains('date', 'exam_id')
	def _check_date_in_exam_range(self):
		for line in self:
			if not line.date or not line.exam_id:
				continue
			start = line.exam_id.start_date
			end = line.exam_id.end_date
			if start and end and not (start <= line.date <= end):
				raise ValidationError(_(
					"Subject line date %(date)s must be between exam start date %(start)s and end date %(end)s."
				) % {
					'date': line.date,
					'start': start,
					'end': end,
				})

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


	@api.depends('name')
	def _compute_display_name(self):
		for rec in self:
			rec.display_name = '%s' % rec.name

   

class StudentExam(models.Model):
	_name = 'student.exam'
	_description = 'Generate Student Exams'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]
	_check_company_auto = True

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
	

	@api.constrains('company_id', 'standard', 'division', 'class_id', 'start_date', 'end_date')
	def _check_duplicate_exam(self):
		for rec in self:
			existing_exam = self.env['student.exam'].search([
				('company_id', '=', rec.company_id.id),
				('standard', '=', rec.standard.id),
				('division', '=', rec.division.id),
				('class_id', '=', rec.class_id.id),
				('start_date', '=', rec.start_date),
				('end_date', '=', rec.end_date),
				('id', '!=', rec.id)
			])
			if existing_exam:
				raise ValidationError("Exam with similar standard, division and class already exists")			

	company_id = fields.Many2one(
		'res.company',
		string='Company',
		required=True,
		index=True,
		default=lambda self: self.env.company,
		tracking=True,
	)
	student_ids = fields.Many2many(
		'res.partner', domain=[('is_student', '=', True)],
		check_company=True)
	student_domain = fields.Char(
		compute='_compute_student_domain',
		string='Student Domain',
	)
	name = fields.Char(string='Name')
	start_date = fields.Date('Start Date')
	end_date = fields.Date('End Date')
	subject_line = fields.One2many(
		'subject.line', 'exam_id', string='Subjects')
	standard = fields.Many2one(
		'student.standard', string="Standard")
	division = fields.Many2one(
		'standard.division', string="Division")
	class_id = fields.Many2one(
		'student.class', string='الفصل', tracking=True)
	curr_year = fields.Many2one('year.year', string='Year')
	state = fields.Selection([('draft', 'Draft'), ('ongoing', 'On Going'),
							  ('close', 'Closed'), ('cancel', 'Canceled')], default='draft')

	time_from = fields.Float(string='Time From', help="Start time")
	time_to = fields.Float(string='Time To', help="Finish time")
	is_annual = fields.Boolean('Is Annual ?')

	def _get_student_domain(self):
		"""Progressive domain: company+standard required; division/class/year only if set."""
		self.ensure_one()
		domain = [('is_student', '=', True)]
		if self.company_id:
			domain.append(('company_id', '=', self.company_id.id))
		if self.standard:
			domain.append(('standard', '=', self.standard.id))
		if self.division:
			domain.append(('div', '=', self.division.id))
		if self.class_id:
			domain.append(('class_id', '=', self.class_id.id))
		if self.curr_year:
			domain.append(('curr_year', '=', self.curr_year.id))
		return domain

	@api.depends('company_id', 'standard', 'division', 'class_id', 'curr_year')
	def _compute_student_domain(self):
		for exam in self:
			exam.student_domain = str(exam._get_student_domain())

	@api.onchange('company_id', 'standard', 'division', 'class_id', 'curr_year')
	def _onchange_student_filters(self):
		"""Load/update students as filters are refined.

		- company + standard → load matching students
		- adding division / class / year → refine the list
		"""
		domain = self._get_student_domain()
		if not self.company_id or not self.standard:
			self.student_ids = [(5, 0, 0)]
		else:
			students = self.env['res.partner'].search(domain, order='roll_no, name')
			self.student_ids = [(6, 0, students.ids)]
		return {'domain': {'student_ids': domain}}

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
					'sequence': (i + 1) * 10,
					'date': exam_date,
					'day': day_name,
					'time_from': self.time_from,
					'time_to': self.time_to,
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

	def action_print_exam_schedule(self):
		self.ensure_one()
		lang = self.env.lang if (self.env.lang or '').startswith('ar') else 'ar_001'
		return self.env.ref(
			'jt_education_exam.action_report_exam_schedule'
		).with_context(lang=lang).report_action(self)

	def get_asset_data_uri(self, filename):
		"""Return a data URI for a logo so wkhtmltopdf does not need HTTP."""
		module_path = get_module_path('jt_education_exam')
		path = os.path.join(module_path, 'static', 'assets', filename)
		if not os.path.isfile(path):
			return ''
		with open(path, 'rb') as handle:
			encoded = base64.b64encode(handle.read()).decode('ascii')
		ext = os.path.splitext(filename)[1].lower().lstrip('.') or 'png'
		mime = 'jpeg' if ext in ('jpg', 'jpeg') else ext
		return 'data:image/%s;base64,%s' % (mime, encoded)

	def get_arabic_font_face_css(self):
		fonts = (
			('normal', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
			('bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
		)
		rules = []
		for weight, path in fonts:
			if not os.path.isfile(path):
				continue
			with open(path, 'rb') as handle:
				encoded = base64.b64encode(handle.read()).decode('ascii')
			rules.append(
				"@font-face{"
				"font-family:'ReportArabic';"
				"src:url(data:font/truetype;charset=utf-8;base64,%s) format('truetype');"
				"font-weight:%s;font-style:normal;}"
				% (encoded, weight)
			)
		return Markup(''.join(rules))

	def format_float_time(self, value):
		value = value or 0.0
		hours = int(value)
		minutes = int(round((value - hours) * 60))
		if minutes == 60:
			hours += 1
			minutes = 0
		return '%02d:%02d' % (hours, minutes)

	def get_day_label_ar(self, day_key):
		return DAY_LABELS_AR.get(day_key or '', day_key or '')

	def get_schedule_lines(self):
		"""Ordered subject lines for the examination schedule report."""
		self.ensure_one()
		return self.subject_line.sorted(key=lambda line: (line.sequence, line.date or fields.Date.today(), line.id))


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
