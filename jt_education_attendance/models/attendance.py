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
    _check_company_auto = True
    _inherit = [
                'mail.thread',
                'mail.activity.mixin',
            
               ]

    name = fields.Char(string='الاسم', compute='_compute_name', store=True)
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    standard_id = fields.Many2one('student.standard')
    division_id = fields.Many2one('standard.division')
    class_id = fields.Many2one('student.class', string='الفصل')
    subject_id = fields.Many2many('student.subject', string="Subjects")
    date = fields.Date(string="Date", default=fields.Date.today())
    attendance_ids = fields.One2many('attendance.line', 'attendance_id', string="Attendance Line")
    student_id = fields.Many2one('res.partner', string="Students", domain=[('is_student', '=', True)])

    _standard_division_class_date_uniq = models.Constraint(
        'UNIQUE(company_id, standard_id, division_id, class_id, date)',
        'سجل الحضور لهذا الصف والشعبة والفصل موجود بالفعل!',
    )

    def _get_student_domain(self):
        self.ensure_one()
        domain = [
            ('is_student', '=', True),
            ('standard', '=', self.standard_id.id),
            ('div', '=', self.division_id.id),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ]
        if self.class_id:
            domain.append(('class_id', '=', self.class_id.id))
        return domain

    @api.onchange('standard_id', 'division_id', 'class_id', 'company_id')
    def onchange_standard_division(self):
        attendance_lines = [(5, 0)]
        if not (self.standard_id and self.division_id and self.company_id):
            self.attendance_ids = attendance_lines
            return

        students = self.env['res.partner'].search(self._get_student_domain())
        for student in students:
            attendance_lines.append((0, 0, {
                'student_id': student.id,
                'attendance_id': self.id,
            }))
        self.attendance_ids = attendance_lines

    def select_all_line(self):
        all_selected = all(line.selected for line in self.attendance_ids)

        for line in self.attendance_ids:
            line.selected = not all_selected
            

    @api.depends(
        'company_id.name',
        'date',
        'division_id.name',
        'standard_id.name',
        'class_id.name',
    )
    def _compute_name(self):
        for rec in self:
            grade_parts = [
                part for part in [
                    rec.division_id.name,
                    rec.standard_id.name,
                    rec.class_id.name,
                ] if part
            ]
            name_parts = [
                part for part in [
                    rec.company_id.name,
                    fields.Date.to_string(rec.date) if rec.date else False,
                    '-'.join(grade_parts) if grade_parts else False,
                ] if part
            ]
            rec.name = ' '.join(name_parts) or _('حضور الطلاب')

    @api.depends('name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.name or _('حضور الطلاب')

    def _apply_attendance_status(self, status):
        """Set status on selected lines and clear conflicting flags."""
        status_values = {
            'present': {
                'present': True,
                'absence_reason': False,
                'absence_noreason': False,
                'late': False,
                'withdraw': False,
            },
            'absence_reason': {
                'present': False,
                'absence_reason': True,
                'absence_noreason': False,
                'late': False,
                'withdraw': False,
            },
            'absence_noreason': {
                'present': False,
                'absence_reason': False,
                'absence_noreason': True,
                'late': False,
                'withdraw': False,
            },
            'late': {
                'present': True,
                'absence_reason': False,
                'absence_noreason': False,
                'late': True,
                'withdraw': False,
            },
            'withdraw': {
                'present': False,
                'absence_reason': False,
                'absence_noreason': False,
                'late': False,
                'withdraw': True,
            },
        }
        values = status_values[status]
        for line in self.attendance_ids.filtered(lambda x: x.selected):
            line.write({**values, 'selected': False})

    def present_student(self):
        self._apply_attendance_status('present')

    def absence_noreason_student(self):
        self._apply_attendance_status('absence_noreason')

    def absence_reason_student(self):
        self._apply_attendance_status('absence_reason')

    def withdraw_student(self):
        self._apply_attendance_status('withdraw')

    def late_student(self):
        self._apply_attendance_status('late')


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
    #                 })
    #     else:
    #         raise ValidationError("Enter Student Details")

class AttendanceLine(models.Model):
    _name = 'attendance.line'
    _description = "Student Attendance Line"
    _check_company_auto = True
    _order = 'date desc, id desc'

    attendance_id = fields.Many2one('attendance.attendance', string="Attendance", ondelete='cascade')
    name = fields.Char(related='student_id.name', string="Name", help="Student List is displayed based on standard, division and class.")
    student_id = fields.Many2one(
        'res.partner',
        string="Students",
        domain=[('is_student', '=', True)],
        index=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='attendance_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    roll_no = fields.Integer(related='student_id.roll_no', string="Roll Number")
    present = fields.Boolean(string="Present")
    absence_reason = fields.Boolean(string="Absent with Reason")
    absence_noreason = fields.Boolean(string="Absent with no Reason")
    late = fields.Boolean(string="Late")
    withdraw = fields.Boolean(string="Withdraw")
    standard_id = fields.Many2one('student.standard', related="attendance_id.standard_id", store=True)
    division_id = fields.Many2one('standard.division', related="attendance_id.division_id", store=True)
    class_id = fields.Many2one('student.class', related="attendance_id.class_id", store=True)
    selected = fields.Boolean("Select")
    date = fields.Date(string="Date", related="attendance_id.date", store=True, index=True)
    status = fields.Selection(
        [
            ('present', 'حاضر'),
            ('absence_reason', 'غائب بسبب'),
            ('absence_noreason', 'غائب بدون سبب'),
            ('late', 'متأخر'),
            ('withdraw', 'سحب'),
            ('none', 'غير محدد'),
        ],
        string='الحالة',
        compute='_compute_status',
        store=True,
    )

    @api.depends('present', 'absence_reason', 'absence_noreason', 'late', 'withdraw')
    def _compute_status(self):
        for line in self:
            if line.withdraw:
                line.status = 'withdraw'
            elif line.absence_reason:
                line.status = 'absence_reason'
            elif line.absence_noreason:
                line.status = 'absence_noreason'
            elif line.late:
                line.status = 'late'
            elif line.present:
                line.status = 'present'
            else:
                line.status = 'none'

    @api.onchange('student_id')
    def onchange_student_id(self):        
        if self.student_id:
            existing_record = self.search([
                ('student_id', '=', self.student_id.id)])
            if existing_record:
                raise exceptions.ValidationError(_('Attendance for this student  already exists!'))

    
