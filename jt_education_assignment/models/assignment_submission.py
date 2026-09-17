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

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StudentAssignmentSubmission(models.Model):
	_name = "student.assignment.submission"
	_inherit = "mail.thread"
	_description = "Assignment Submission"
	_rec_name = 'assignment_id'

	assignment_id = fields.Many2one(
		'student.assignment',string='Assignment', help="Enter Students to see assignments assigned to them.")
	student_id = fields.Many2many(
		'res.partner', string='Students', domain=[('is_student', '=', True)])
	description = fields.Text('Description')
	state = fields.Selection([
		('draft', 'Draft'), ('submit', 'Submitted'), ('reject', 'Rejected'),
		('change', 'Change Req.'), ('accept', 'Accepted')],string='State',
		default='draft')
	submission_date = fields.Datetime(
		'Submission Date', readonly=True,
		default=lambda self: fields.Datetime.now())
	marks = fields.Float(related='assignment_id.marks')
	marks_scored = fields.Float('Scored Marks')
	note = fields.Text('Note')
	active = fields.Boolean(default=True)
	standard_id = fields.Many2one('student.standard',related="assignment_id.standard_id",string="Standard")
	division_id = fields.Many2one('standard.division',related="assignment_id.division_id",string="Division")
	curr_year = fields.Many2one('year.year',related="assignment_id.curr_year", string="Year")
	faculty_id = fields.Many2one('res.partner',related="assignment_id.faculty",string="Faculty")
	attachment = fields.Many2many('ir.attachment', 'attach_rel', 'doc_id','attach_id3',string="Attachment",help='You can attach the copy of your document', copy=False)
	student_submission_ids = fields.One2many('student.submission.line','submission_id', string="Students ")

	@api.onchange('assignment_id')
	def onchange_assignment(self):
		student_lines = [(5, 0)]
		assignment = self.assignment_id

		if assignment:
			allocated_students = assignment.allocation_ids

			for student in allocated_students:
				student_lines.append((0, 0, {
					'student_id': student.id,
					'submission_id': self.id,
				}))

		self.student_submission_ids = student_lines

	@api.depends('assignment_id.name', 'standard_id.name', 'division_id.name')
	def _compute_display_name(self):
		for rec in self:
			rec.display_name = '%s(%s-%s)' % (
				rec.assignment_id.name or '',
				rec.standard_id.name or '',
				rec.division_id.name or '',
			)

	def act_draft(self):
		result = self.state = 'draft'
		return result and result or False

	def act_submit(self):
		result = self.state = 'submit'
		return result and result or False

	def act_accept(self):
		result = self.state = 'accept'
		return result and result or False

	def act_change_req(self):
		result = self.state = 'change'
		return result and result or False

	def act_reject(self):
		result = self.state = 'reject'
		return result and result or False
class studentSubmission(models.Model):
	_inherit = 'res.partner'

	marks_scored = fields.Float("Scored Marks")
	student_assignment_pdf=fields.Binary(string="Upload Assignment")
	student_assignment_pdf_file=fields.Char(string="Upload Assignment ")

class StudentSubmissionLine(models.Model):
	_name = 'student.submission.line'
	_description = 'Student Submission Line'
	_rec_name = 'student_id'
	
	submission_id = fields.Many2one('student.assignment.submission',)
	student_id = fields.Many2one('res.partner', string="Students", domain=[('is_student', '=', True)])
	marks_scored = fields.Float("Scored Marks")
	student_assignment_pdf=fields.Binary(string="Upload Assignment")
	student_assignment_pdf_file=fields.Char(string="Upload Assignment ")
	assignment_submission_id = fields.Many2one('student.assignment', string="Assignment")
	


	@api.constrains('marks_scored')
	def check_scored_marks(self):
		for record in self:
			total_marks = record.submission_id.marks
			if record.marks_scored > total_marks:
				raise ValidationError(f"Scored Marks cannot be greater than Total Marks.")

class AttachmentSubmission(models.Model):

	_inherit = 'ir.attachment'

	attach_rel = fields.Many2many('res.partner', 'attachment', 'attachment_id3', 'document_id',string="Attachment")
