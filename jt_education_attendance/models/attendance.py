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
from odoo import fields, models, api, exceptions, _
from odoo.exceptions import ValidationError,UserError

class Attendance(models.Model):
    _name = 'attendance.attendance'
    _description = "Student Attendance"
    _rec_name = 'date'
    _inherit = [
                'mail.thread',
                'mail.activity.mixin',
            
               ]

    faculty_id = fields.Many2one('res.partner', domain=[('is_faculty', '=', True)])
    standard_id = fields.Many2one('student.standard')
    division_id = fields.Many2one('standard.division')
    subject_id = fields.Many2many('student.subject', string="Subjects")
    date = fields.Date(string="Date", default=fields.Date.today())
    attendance_ids = fields.One2many('attendance.line', 'attendance_id', string="Attendance Line")
    student_id = fields.Many2one('res.partner', string="Students", domain=[('is_student', '=', True)])

    _faculty_standard_date_uniq = models.Constraint(
        'UNIQUE(faculty_id, standard_id, division_id, date)',
        'Attendance for this faculty and standard already exists!',
    )


    @api.onchange('standard_id', 'division_id')
    def onchange_standard_division(self):
        attendance_lines = [(5, 0)]
        students = self.env['res.partner'].search([
            ('is_student', '=', True),
            ('standard', '=', self.standard_id.id),
            ('div', '=', self.division_id.id)
        ])
        
        for student in students:
            attendance_lines.append((0, 0, {
                'student_id': student.id,
                'attendance_id':self.id,
                'faculty_id': self.faculty_id.id,

            }))
        
        self.attendance_ids = attendance_lines

   
   

    def select_all_line(self):
        all_selected = all(line.selected for line in self.attendance_ids)

        for line in self.attendance_ids:
            line.selected = not all_selected
            

    @api.depends('faculty_id.name', 'standard_id.name', 'division_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s - %s(%s)' % (
                rec.faculty_id.name or '',
                rec.standard_id.name or '',
                rec.division_id.name or '',
            )

    def present_student(self):
        if self.attendance_ids:
            for line in self.attendance_ids.filtered(lambda x:x.selected):
                if line.absence_reason == True or line.absence_noreason == True or line.withdraw == True:
                    line.present = False
                else:
                    line.present = True
                line.selected = False

    def absence_noreason_student(self):
        if self.attendance_ids:
            for line in self.attendance_ids.filtered(lambda x:x.selected):
                if line.present == False and line.absence_reason == False and line.withdraw == False:
                    line.absence_noreason = True            
                line.selected = False

    def absence_reason_student(self):
        if self.attendance_ids:
            for line in self.attendance_ids.filtered(lambda x:x.selected):
                if line.present == False and line.absence_noreason == False and line.withdraw == False:
                    line.absence_reason = True
                line.selected = False


    def withdraw_student(self):
        if self.attendance_ids:
            for line in self.attendance_ids.filtered(lambda x:x.selected):
                if line.absence_reason == True or line.absence_noreason == True:
                    line.withdraw = False
                else:
                    line.withdraw = True
                    line.present = False
                    line.absence_reason = False
                    line.absence_noreason = False
                    line.late = False
                line.selected = False

                    
    def late_student(self):
        if self.attendance_ids:
            for line in self.attendance_ids.filtered(lambda x:x.selected):
                if line.absence_reason == True or line.absence_noreason == True or line.withdraw == True:
                    line.late = False
                else:
                    line.late = True
                    line.present = True
                line.selected = False


    def reminder_absent_student(self):
        try:
            template = self.env.ref('jt_education_attendance.absent_student_template')
        except ValueError:
            raise UserError(_("Email template not found. Please check the template configuration."))

        # Group absent students by parent to send one email per parent with all their absent children
        parent_student_map = {}
        
        for record in self.attendance_ids:
            if record.absence_reason or record.absence_noreason:
                parents = self.env['res.partner'].search([
                    ('student_ids', '=', record.student_id.id),
                    ('is_parent', '=', True),
                    ('email', '!=', False),
                ])
                
                for parent in parents:
                    if parent.id not in parent_student_map:
                        parent_student_map[parent.id] = {
                            'parent': parent,
                            'absences': []
                        }
                    parent_student_map[parent.id]['absences'].append(record)

        # Send emails to each parent with all their absent children
        for parent_data in parent_student_map.values():
            parent = parent_data['parent']
            absent_records = parent_data['absences']
            
            email_values = {
                'email_from': self.env.user.email_formatted,
                'email_to': parent.email,
                'subject': _('Attendance Reminder - Absent Students (%s)') % self.date,
            }

            # Prepare the email context with all absent students for this parent
            context = {
                'parent': parent,
                'absent_students': absent_records,
                'date': self.date,
            }

            # Send the email using the template with the appropriate context
            template.with_context(context).send_mail(
                self.id, force_send=True, email_values=email_values
            )

    has_absent_students = fields.Boolean(
        string='Has Absent Students',
        compute='_compute_has_absent_students',
        store=False  # Set to True if you need to search based on this field
    )

    @api.depends('attendance_ids.absence_reason', 'attendance_ids.absence_noreason')
    def _compute_has_absent_students(self):
        for record in self:
            record.has_absent_students = bool(
                record.attendance_ids.filtered(
                    lambda x: x.absence_reason or x.absence_noreason
                )
            )



    
    # def add_student_line(self):
    #     stud_ids = []
    #     if self.attendance_ids:
    #         print("-------self.attendance_ids-------",self.attendance_ids)

    #         for line in self.attendance_ids:
    #             stud_ids.append(line.student_id.id)

    #     students = self.env['res.partner'].search([('is_student', '=', True), ('standard','=',self.standard_id.id), ('div','=',self.division_id.id),('id', 'not in', stud_ids)])
    #     print("-------students-------",students)
    #     if students:
    #         for stud in students:
    #             self.attendance_ids.create({
    #                 'student_id':stud.id,
    #                 'attendance_id':self.id,
    #                 'faculty_id':self.faculty_id.id,
    #                 })
    #     else:
    #         raise ValidationError("Enter Student Details")

class AttendanceLine(models.Model):
    _name = 'attendance.line'
    _description = "Student Attendance Line"

    attendance_id = fields.Many2one('attendance.attendance', string="Attendance")
    name = fields.Char(related='student_id.name', string="Name", help="Student List is displayed based on standard and division.")
    student_id = fields.Many2one('res.partner', string="Students", domain=[('is_student', '=', True)])
    faculty_id = fields.Many2one('res.partner', domain=[('is_faculty', '=', True)], required=True)
    roll_no = fields.Integer(related='student_id.roll_no', string="Roll Number")
    present = fields.Boolean(string="Present")
    absence_reason = fields.Boolean(string="Absent with Reason")
    absence_noreason = fields.Boolean(string="Absent with no Reason")
    late = fields.Boolean(string="Late")
    withdraw = fields.Boolean(string="Withdraw")
    standard_id = fields.Many2one('student.standard',related="attendance_id.standard_id")
    division_id = fields.Many2one('standard.division',related="attendance_id.division_id")
    selected = fields.Boolean("Select")
    date = fields.Date(string="Today's Date",related="attendance_id.date")

    @api.onchange('student_id')
    def onchange_student_id(self):        
        if self.student_id:
            existing_record = self.search([
                ('student_id', '=', self.student_id.id)])
            if existing_record:
                raise exceptions.ValidationError(_('Attendance for this student  already exists!'))

    
