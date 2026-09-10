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
from odoo import models, fields, api,_
from odoo.exceptions import ValidationError,UserError

class TimeTable(models.Model):

	_name = "student.timetable"
	_description = "Student Timetable"
	

	name = fields.Char("Name")
	standard = fields.Many2one('student.standard', string='Standard')
	division = fields.Many2one('standard.division', string='Division')
	curr_year = fields.Many2one('year.year', string='Academic Year')
	duration = fields.Float("Duration")
	lec_start_time = fields.Float("Start Time")
	timetable_mon = fields.One2many('student.timetable.line', 'timetable_id',
									domain=[('week_day', '=', '0')])
	timetable_tue = fields.One2many('student.timetable.line', 'timetable_id',
									domain=[('week_day', '=', '1')])
	timetable_wed = fields.One2many('student.timetable.line', 'timetable_id',
									domain=[('week_day', '=', '2')])
	timetable_thur = fields.One2many('student.timetable.line', 'timetable_id',
									 domain=[('week_day', '=', '3')])
	timetable_fri = fields.One2many('student.timetable.line', 'timetable_id',
									domain=[('week_day', '=', '4')])
	timetable_sat = fields.One2many('student.timetable.line', 'timetable_id',
									domain=[('week_day', '=', '5')])
	timetable_sun = fields.One2many('student.timetable.line', 'timetable_id',
									domain=[('week_day', '=', '6')])
	student_ids = fields.Many2many('res.partner', string='Student',domain="[('is_student','=', true)]")
	state = fields.Selection([('draft','Draft'),('validate','Validate')], default="draft")

	def timetable_validate(self):
		self.state = 'validate'


	@api.constrains('standard', 'division', 'curr_year')
	def _check_duplicate_timetable(self):
		for rec in self:
			existing_timetable = self.search([
				('standard', '=', rec.standard.id),
				('division', '=', rec.division.id),
				('curr_year', '=', rec.curr_year.id),
				('id', '!=', rec.id)
			])
			if existing_timetable:
				raise ValidationError("Timetable already exists")

	def create(self, vals):
		"""To generate name for the model"""
		standard_val = vals.get('standard')
		division_val = vals.get('division')
		curr_year_val = vals.get('curr_year')
		if standard_val:
			standard = self.env['student.standard'].browse(standard_val)
			standard_name = standard.name
			if division_val:
				division = self.env['standard.division'].browse(division_val)
				division_name = division.name
				if curr_year_val:
					curr_year = self.env['year.year'].browse(curr_year_val)
					curr_year_name = curr_year.name
			vals['name'] = f"{standard_name}/{division_name}/{curr_year_name}"
		else:
			vals['name'] = ''

		return super(TimeTable, self).create(vals)

	def write(self, vals):
		res = super(TimeTable, self).write(vals)
		if 'duration' in vals or 'lec_start_time' in vals:
			line_obj = self.env['student.timetable.line']
			for rec in self:
				start_time =  rec.lec_start_time
				duration = rec.duration
				for day in range(6):
					line_ids = line_obj.search([('timetable_id', '=', rec.id),('week_day','=',str(day))], order="time_from")
					time_from = start_time  			
					for line in line_ids:
						line.time_from = time_from						
						line.time_till = time_from + duration						
						time_from = line.time_till
					
		return res


class TimeTableLine(models.Model):

	_name = "student.timetable.line"
	_description = "Student Timetable Line"

	# period_id = fields.Many2one('timetable.period', string="Period")
	time_from = fields.Float("From")
	time_till = fields.Float("To")
	subject = fields.Many2one('student.subject', string='Subjects')
	faculty_id = fields.Many2one('res.partner', string='Faculty',domain=[('is_faculty', '=', True)])
	week_day = fields.Selection([
		('0', 'Monday'),
		('1', 'Tuesday'),
		('2', 'Wednesday'),
		('3', 'Thursday'),
		('4', 'Friday'),
		('5', 'Saturday'),
		('6', 'Sunday'),
	], 'Day')
	timetable_id = fields.Many2one('student.timetable')
	date = fields.Date("Date")
	sequence = fields.Integer()


	@api.model_create_multi
	def create(self, vals):
		res = super(TimeTableLine, self).create(vals)
		for rec in res:
			start_time = rec.timetable_id.lec_start_time
			duration = rec.timetable_id.duration
			if start_time and duration:
				last_lines = self.search([
					('timetable_id', '=', rec.timetable_id.id),
					('week_day', '=', rec.week_day)
				])
				time_from = start_time
				for line in last_lines:
					if line.time_till > time_from:
						time_from = line.time_till


				rec.time_from = time_from
				rec.time_till = time_from + duration     
			
		return res

	# @api.onchange('sequence')
	# def _onchange_sequence(self):
	# 	print("sequence-------------------",self.sequence)
	# 	start_time = self.timetable_id.lec_start_time
	# 	duration = self.timetable_id.duration

	# 	if start_time and duration:
	# 		last_lines = self.search([
	# 			('timetable_id', '=', self.timetable_id.id),
	# 			('week_day', '=', self.week_day)
	# 		])

	# 		time_from = start_time
	# 		for line in last_lines:
	# 			if line.time_till > time_from:
	# 				time_from = line.time_till

	# 		self.time_from = time_from
	# 		self.time_till = time_from + duration



class TimetablePeriod(models.Model):
	_name = 'timetable.period'
	_description = 'Timetable Period'

	name = fields.Char(string="Name")
	time_from = fields.Float(string='From')
	time_to = fields.Float(string='To')


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
