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
from odoo import models, fields, api,exceptions,_
from odoo.exceptions import ValidationError,UserError
import base64


class ExamResult(models.Model):
	_name = 'student.result'
	_description = 'Generate Student Result'
	_rec_name = 'student_id'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]
	

	@api.depends('student_id.stud_id', 'student_id.name', 'exam_id.name')
	def _compute_display_name(self):
		for rec in self:
			rec.display_name = '%s-%s (%s)' % (
				rec.student_id.stud_id or '',
				rec.student_id.name or '',
				rec.exam_id.name or '',
			)

	student_id = fields.Many2one('res.partner', string='Student', domain=[
								 ('is_student', '=', True)])
	standard = fields.Many2one(related="student_id.standard",store=True)
	division = fields.Many2one(related="student_id.div",store=True)
	academic_year = fields.Many2one(related='student_id.curr_year', store=True,string="Year")
	exam_id = fields.Many2one('student.exam', string='Exam', domain=[('state','=','close')])
	subject_line = fields.One2many(
		'result.subject.line', 'result_id', string='Subjects')
	total_pass_mark = fields.Float(
		string='Total Passing Marks', store=True, readonly=True, compute='_total_marks_all')
	total_mark = fields.Float(
		string='Total Marks', store=True, readonly=True, compute='_total_marks_all')
	total_mark_scored = fields.Float(
		string='Total Marks Scored', store=True, readonly=True, compute='_total_marks_all')
	pass_fail_full = fields.Boolean(
		string='Pass/Fail', store=True, readonly=True, compute='_total_marks_all')
	percentage = fields.Float('Percentage %',compute='_compute_percentage') 
	input_line = fields.Html("Remarks")
	faculty_id = fields.Many2one('res.partner', domain=[('is_faculty', '=', True)])
	parent_id = fields.Many2one('res.partner', domain=[('is_parent', '=', True)])
	english_id = fields.Many2one('res.partner', domain=[('is_faculty', '=', True)], string="English Teacher")
	chineses_id = fields.Many2one('res.partner', domain=[('is_faculty', '=', True)], string="Chinese Teacher")
	leo_id = fields.Many2one('res.partner', domain=[('is_faculty', '=', True)], string="Leo Teacher")
	grade_id = fields.Many2one('result.grade',string="Grade",compute="get_grade_id", store=True)
	english_description = fields.Text( string="English Description")
	chineses_description = fields.Text( string="Chinese Description")
	leo_description = fields.Text(string="Leo Description")
	parent_description = fields.Text(string="Parent Description")
	is_result_annual = fields.Boolean("Is Annual")

	def action_send_result_mail(self):
		# Reference the result report template
		report_template_id = self.env['ir.actions.report']._render_qweb_pdf('jt_education_exam.result_report_template', res_ids=self.id)
		
		# Encode the PDF
		data_record = base64.b64encode(report_template_id[0])
		
		# Create IR attachment
		ir_values = {
			'name': f"Result_{self.exam_id.name}_{self.student_id.name}.pdf",
			'type': 'binary',
			'datas': data_record,
			'store_fname': f"Result_{self.exam_id.name}_{self.student_id.name}.pdf",
			'mimetype': 'application/x-pdf',
		}
		data_id = self.env['ir.attachment'].create(ir_values)
		
		template = self.env.ref('jt_education_exam.result_created_template')
		
		template.attachment_ids = [(6, 0, [data_id.id])]
		
		# Prepare email values
		email_values = {
			'email_to': self.student_id.email,
			'email_from': self.env.user.email_formatted,
		}
		
		try:
			template.send_mail(self.id, email_values=email_values, force_send=True)
		except Exception as e:
			raise UserError(_("An error occurred while sending the email: %s") % str(e))
		
		# Remove attachment after sending
		template.attachment_ids = [(3, data_id.id)]
		
		return True



	@api.onchange('exam_id')
	def _onchange_exam_bul_id(self):
		print("hello++++++++++++")
		if self.exam_id and self.exam_id.is_annual:
			self.is_result_annual = True
		else:
			self.is_result_annual = False

	@api.depends('is_result_annual', 'percentage')
	def calculate_student_percentage(self):
		for record in self:
			# Check if the result is annual and if the student_id is present
			if record.is_result_annual and record.student_id:
				record.student_id.student_result = record.percentage



	@api.model
	def calculate_student_ranks(self):
		# count the average percentage for each studentss
		student_avg_percentage = {}
		
		all_results = self.search([])
		print("All student results fetched:", all_results)
		for result in all_results:
			student = result.student_id
			if student not in student_avg_percentage:
				student_avg_percentage[student] = {
					'total_percentage': 0.0,
					'exam_count': 0
				}
			student_avg_percentage[student]['total_percentage'] += result.percentage
			student_avg_percentage[student]['exam_count'] += 1
			print(f"updated totals for {student.name}: {student_avg_percentage[student]}")

		
		# count avg for all studentsss
		student_avg_percentage = {
			student: values['total_percentage'] / values['exam_count']
			for student, values in student_avg_percentage.items()
		}
		print("student average percentages calculated:", student_avg_percentage)


		# rank
		sorted_students = sorted(student_avg_percentage.items(), key=lambda item: item[1], reverse=True)
		print("Sorted students by average percentage:", sorted_students)

		
		# update the rank in the student record
		rank = 1
		for student, avg_percentage in sorted_students:
			print(f"Assigning rank {rank} to {student.name} with average percentage {avg_percentage}")

			student.write({'student_rank': rank})
			rank += 1
		print("Ranking update complete for all students.")

	

	@api.depends('percentage')
	def get_grade_id(self):
		grade_ids = self.env['result.grade'].search([])
		for line in self:
			for grade in grade_ids:
				grade_data = grade.mark_range.split('-')
				if int(line.percentage) in range(int(grade_data[0]),int(grade_data[1])):
					line.grade_id = grade.id
					break;
				else:
					line.grade_id =False

	@api.constrains('student_id', 'exam_id')
	def _check_unique_student_exam(self):
		for rec in self:
			existing_result = self.search([
				('student_id', '=', rec.student_id.id),
				('exam_id', '=', rec.exam_id.id),
				('id', '!=', rec.id)
			])
			if existing_result:
				raise exceptions.ValidationError("Result for this already created")
				

	@api.onchange('exam_id')
	def _onchange_exam_id(self):
		if self.exam_id:
			subject_line_data = [(5, 0, 0)]
			for subject_line in self.exam_id.subject_line:
				line = (0, 0, {
				'subject_id': subject_line.subject_id.id,
				'date': subject_line.date,
				'subject_category_id': subject_line.subject_id.subject_category_id.id,
				'exam_id':self.exam_id.id,
				'student_id':self.student_id.id,
				})
				subject_line_data.append(line)
			self.subject_line = subject_line_data




	@api.depends('subject_line.mark_scored')
	def _total_marks_all(self):
		for results in self:
			total_pass_mark = 0
			total_mark = 0
			total_mark_scored = 0
			pass_fail_full = True
			for subjects in results.subject_line:
				total_pass_mark += subjects.pass_mark
				total_mark += subjects.mark
				total_mark_scored += subjects.mark_scored
				if not subjects.pass_or_fail:
					pass_fail_full = False
			results.total_pass_mark = total_pass_mark
			results.total_mark = total_mark
			results.total_mark_scored = total_mark_scored
			results.pass_fail_full = pass_fail_full

	@api.depends('subject_line')
	def _compute_percentage(self):
		for record in self:
		# Percentage = (Value ⁄ Total Value) × 100
			record.percentage = (record.total_mark_scored/record.total_mark)*100 if record.total_mark != 0 else 0
		# print("percentage..........",self.percentage)
			


	def get_gread_records(self):
		return self.env['result.grade'].search([])

	

class ResultSubjectLine(models.Model):
	_name = 'result.subject.line'
	_description = "Result Subject Line"
	
	mark = fields.Float('Marks',compute="_compute_category_marks",store=True)
	pass_mark = fields.Float('Passing Marks',compute="_compute_category_marks",store=True)
	mark_scored = fields.Float('Marks Scored',store=True)
	pass_or_fail = fields.Boolean('Pass/Fail',compute="_compute_category_marks",store=True)
	result_id = fields.Many2one('student.result', string='Result Id')
	student_id = fields.Many2one('res.partner', string='Student',related="result_id.student_id",store=True)
	academic_year = fields.Many2one(related='student_id.curr_year', store=True)
	date = fields.Date(string='Date')
	exam_id = fields.Many2one('student.exam', string='Exam', store=True)
	grade_id = fields.Many2one('result.grade',string="Grade",compute="get_grade_id", store=True)
	standard = fields.Many2one(related="student_id.standard")
	division = fields.Many2one(related="student_id.div")
	academic_year = fields.Many2one(related='student_id.curr_year', store=True)
	subject_id = fields.Many2one('student.subject', string='Subject',required=True,)
	subject_category_id = fields.Many2one("subject.category",string="Subject category",related="subject_id.subject_category_id")
	is_present=fields.Boolean(string="Present")   
	_unique_subject_result = models.Constraint(
		'UNIQUE(subject_id, result_id)',
		'Subject in result must be unique!',
	)


	@api.depends('mark_scored')
	def get_grade_id(self):
		grade_ids = self.env['result.grade'].search([])
		for line in self:
			for grade in grade_ids:
				grade_data = grade.mark_range.split('-')
				if int(line.mark_scored) in range(int(grade_data[0]),int(grade_data[1])):
					line.grade_id = grade.id
					break;
				else:
					line.grade_id =False

	@api.depends('subject_id')
	def _compute_category_marks(self):
		for total_category in self:
			total_category.mark =  total_category.subject_id.mark
			total_category.pass_mark = total_category.subject_id.pass_mark

			if total_category.mark_scored >= 40.00:
				total_category.pass_or_fail = True
			else:
				total_category.pass_or_fail = False

	@api.depends('subject_id')
	def subject_get(self):
		res = []
		for rec in self:
			res.append((rec.id, '%s - %s' % (rec.subject_id)))
		return res

	@api.onchange('subject_id')
	def onchange_subject_id(self):
		self.subject_category_id = self.subject_id.subject_category_id.id 


class Grade(models.Model):
	_name = 'result.grade'
	_description = 'Result Grade'

	name = fields.Char('Grade')
	mark_range = fields.Char('Mark Range')
	latter_grade = fields.Selection([('excellent','Excellent'),('good','Good'),('satisfactory','Satisfactory'),('fails','Fails')],string="Letter Grade")

class SubjectCategory(models.Model):
	_name = 'subject.category'
	_description = 'Subject Category'
	_order = "sequence"

	name = fields.Char('Name') 
	sequence = fields.Integer('Sequence') 

class SubjectCategoryLine(models.Model):
	_name = 'subject.category.line'
	_description = 'Subject Category Line'

	name = fields.Char('Name')
	mark = fields.Float('Marks')
	actual_mark = fields.Float('Actual Marks')
	subject_categ_id = fields.Many2one('subject.category',string="category")
	subject_for_id = fields.Many2one('student.subject',string="standard")
	subject_line_data_id = fields.Many2one('result.subject.line',string="subject line")
	pass_mark = fields.Float('Passing Marks')





class ResPartner(models.Model):
	_name = 'res.partner'
	_inherit = ['res.partner']
	_description = 'Student Information'


	student_result_ids = fields.One2many('student.result', 'student_id', string="Student Result History")
	student_yearly_result_ids = fields.One2many(
        'student.yearly.result', 'student_id', string="Student Yearly Results", compute='_compute_student_yearly_results')
	
	@api.depends('student_result_ids')
	def _compute_student_yearly_results(self):
		StudentYearlyResult = self.env['student.yearly.result']
		
		for partner in self:
			print(f"Processing partner: {partner.name} (ID: {partner.id})")
			
			yearly_data = {}
			current_results = []
			
			# Step 1: Group results by year and identify current academic year results
			for result in partner.student_result_ids:
				year = result.academic_year.id
				current_results.append(year)
				
				if year not in yearly_data:
					yearly_data[year] = {
						'standard': result.standard.id,
						'year': result.academic_year.id,
						'total_rank': result.student_id.student_rank,
						'stu_percentage': result.percentage if result.is_result_annual else 0.0,
						'count': 1
					}
				else:
					yearly_data[year]['total_rank'] += result.student_id.student_rank
					yearly_data[year]['count'] += 1

					if result.is_result_annual:
						yearly_data[year]['stu_percentage'] = result.percentage

			# Step 2: Only delete and recreate records for current academic years
			existing_records = StudentYearlyResult.search([
				('student_id', '=', partner.id),
				('year', 'in', current_results)
			])
			existing_records.unlink()

			# Step 3: Create/Update records only for current years
			new_records = []
			
			# Get existing historical records (preserve them)
			historical_records = StudentYearlyResult.search([
				('student_id', '=', partner.id),
				('year', 'not in', current_results)
			])
			new_records.extend(historical_records.ids)

			# Create new records for current years
			for year, data in yearly_data.items():
				average_rank = data['total_rank'] // data['count'] if data['count'] > 0 else 0
				vals = {
					'student_id': partner.id,
					'year': data['year'],
					'standard': data['standard'],
					'average_rank': average_rank,
					'stu_percentage': data['stu_percentage']
				}
				new_record = StudentYearlyResult.create(vals)
				new_records.append(new_record.id)
			
			# Combine historical and new records
			partner.student_yearly_result_ids = [(6, 0, new_records)]
	

	# @api.onchange('curr_year')

	# @api.model
	# def _compute_student_yearly_results(self):
	# 	for rec in self:
	# 		if rec.curr_year:
	# 			rec.student_yearly_result_ids = [(0,0,{'student_id':rec.id,'year':1, 'standard' :1,'average_rank':1})]
	# 			print("student_yearly_result_ids", rec.student_yearly_result_ids)
	# 		# else:
	# 		# 	rec.student_yearly_result_ids = False

	





class StudentYearlyResult(models.Model):
    _name = 'student.yearly.result'
    _description = 'Aggregated Student Results by Year'

    student_id = fields.Many2one('res.partner', string="Student")
    year = fields.Many2one('year.year', string="Academic Year", required=True)
    standard = fields.Many2one('student.standard', string="Standard", required=True)
    average_rank = fields.Integer(string="Rank")
    stu_percentage = fields.Float('Percentage')

    _unique_student_year = models.Constraint(
        'UNIQUE(student_id, year)',
        'A yearly result already exists for this student and academic year!',
    )

    def print_certificate(self):
    	return self.env.ref('jt_education_base.report_student_certi_template').report_action(self)

	