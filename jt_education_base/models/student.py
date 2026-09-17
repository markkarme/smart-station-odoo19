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
from datetime import date, timedelta

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError, UserError


class ResPartner(models.Model):
    _inherit = "res.partner"
    _description = 'Student Information'

    def unlink(self):
        for record in self:
            if record.is_student and record.standard:
                standard_record = record.standard.sudo()
                if standard_record.occupied_seats > 0:
                    standard_record.write({
                        'occupied_seats': standard_record.occupied_seats - 1,
                        'vacant_seates': standard_record.capacity - (standard_record.occupied_seats - 1),
                    })
        return super().unlink()

    @api.depends('complete_name', 'email', 'vat', 'state_id', 'country_id', 'commercial_company_name',
                 'stud_id', 'faculty_id', 'parents_id', 'is_student', 'is_faculty', 'is_parent')
    @api.depends_context(
        'show_address', 'partner_show_db_id',
        'show_email', 'show_vat', 'lang', 'formatted_display_name'
    )
    def _compute_display_name(self):
        super()._compute_display_name()
        for rec in self:
            prefix = False
            if rec.is_student and rec.stud_id:
                prefix = rec.stud_id
            elif rec.is_faculty and rec.faculty_id:
                prefix = rec.faculty_id
            elif rec.is_parent and rec.parents_id:
                prefix = rec.parents_id
            if prefix and rec.display_name and not rec.display_name.startswith(prefix):
                rec.display_name = '%s - %s' % (prefix, rec.display_name)

    is_student = fields.Boolean('Student')
    mobile = fields.Char(string='Mobile')
    title = fields.Selection(
        [('miss', 'Miss'), ('mrs', 'Mrs'), ('mr', 'Mr')],
        string="Title",
    )
    standard = fields.Many2one('student.standard', 'Standard', help="Add Standard of student")
    div = fields.Many2one('standard.division', help="Add Division of student")
    curr_year = fields.Many2one('year.year', 'Current Year', help="Add current year of student")
    stud_id = fields.Char('Student ID', copy=False, help="Student ID")
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], default='male')
    working_days = fields.Char('Number of Working Days', size=3, help="Total Number of Working Days")
    working_days_present = fields.Char('Number of Working Days Present', size=3, help="Total Number of days present")
    lc_apply_date = fields.Date('Application Date of Leaving Certificate', help="Application Date of Leaving Certificate")
    lc_issue_date = fields.Date('Issue Date of Leaving Certificate', help="Issue Date of Leaving Certificate")
    detension = fields.Char('No. of Time Student is Detained', help="Number of Time Student is Detained")
    promotion = fields.Selection(
        string='Qualified for Promoting to Next Class',
        selection=[('yes', 'Yes'), ('no', 'No')],
    )

    roll_no = fields.Integer('Roll Number', copy=False, help="Roll Number")
    gr_no = fields.Char("GR Number", help="General Registration Number of student")
    father_name = fields.Char('Father Name')
    surname = fields.Char('Surname')
    nickname = fields.Char('Nickname')
    mother_name = fields.Char('Mother Name')
    nationality = fields.Char('Nationality')
    mother_tonque = fields.Char('Mother Tongue')
    religion = fields.Char('Religion')
    caste = fields.Char('Caste')
    subcaste = fields.Char('SubCaste')
    birthPlace = fields.Char('Place of Birth ')
    village = fields.Many2one('village.village', "village")
    province = fields.Many2one('province.province', "Province")
    district_id = fields.Many2one('district.district', 'District')
    state1 = fields.Many2one('res.country.state', 'State ', related="district_id.state")
    country1 = fields.Many2one('res.country', 'Country ', related="district_id.country")
    student_history_ids = fields.One2many('student.history', 'student_id', string="Student History")

    birthdate = fields.Date('Date of Birth ')
    lastschool = fields.Char('Last School Attended', help="Name of last school attended")
    last_std = fields.Char('Last Standard')
    date_admission = fields.Date('Date of admission in this school', help="Enter Date of admission in this school")
    adm_standard = fields.Many2one(
        'student.standard', 'Admission Standard',
        help="Enter Standard in which student got admission in this school",
    )
    application_submission_date = fields.Date(string='Application Submission Date')

    progress = fields.Char('Progress')
    conduct = fields.Char('Conduct')
    howknow_id = fields.Many2one('how.know', 'How Student Know Our School')
    applied_from_website = fields.Boolean('Applied from Website', default=False)
    emergency_contact = fields.Char('Emergency Contact')
    leave_date = fields.Date('Date of Leaving School', help="Date of Leaving this school")
    std_studying = fields.Char('Studying in Standard', help="Studying in Current Standard")
    studying_since = fields.Char('Studying Since', help="Studying Since in this school")
    reason_for_leave = fields.Text('Reason for Leaving school')
    remarks = fields.Text('Remarks')
    signature = fields.Binary("Signature")
    parentsid = fields.Many2one('res.partner', string="Parents", domain=[('is_parent', '=', True)])
    age = fields.Integer("Age", compute='_compute_age', store=True)
    detailed_age = fields.Char("Detailed Age", compute='_compute_age', store=True)
    studend_type = fields.Selection(
        [('person', 'Individual'), ('company', 'Company'), ('student', 'Student'),
         ('faculty', 'Faculty'), ('parent', 'Parent')],
        default="student",
        string="Company Types",
    )
    state = fields.Selection(
        [('draft', 'Pending'), ('confirm', 'Confirm'), ('cancel', 'Cancel')],
        default="draft",
        string="Admission Status",
    )
    marksheet_attachment_pdf = fields.Binary(string="Upload Marksheet")
    marksheet_attachment_pdf_file = fields.Char(string="Upload Marksheet ")
    adhar_attachment_pdf = fields.Binary(string="Upload Adhar Card")
    adhar_attachment_pdf_file = fields.Char(string="Upload Adhar Card ")
    admission_date = fields.Datetime('Admission Date')
    student_rank = fields.Integer('Student Rank')
    student_result = fields.Float('Result Percentage')
    meeting_ids = fields.One2many(comodel_name='student.meeting', inverse_name='student_id', string="Meetings")

    file_registration_number = fields.Char(string="File Registration Number")
    the_total_marks = fields.Integer(string="The Total Marks")
    national_iD_number = fields.Char(string="National ID Number")
    type_of_student = fields.Selection(
        [('male', 'Male'), ('female', 'Female')],
        string="Type of Student",
        default='male',
    )
    telephone_number_3 = fields.Char(string="Telephone Number 3")
    family_ties = fields.Char(string="Family Ties")
    emergency_number = fields.Char(string="Emergency Number")
    fathers_national_ID_number = fields.Char(string="Father's National ID Number")
    fathers_job = fields.Char(string="Father's Job")
    mothers_national_ID_number = fields.Char(string="Mother's National ID Number")
    mothers_job = fields.Char(string="Mother's Job")

    def update_student_ranks(self):
        Result = self.env['student.result'] if 'student.result' in self.env else False
        if Result and hasattr(Result, 'calculate_student_ranks'):
            Result.calculate_student_ranks()
            return True

        students = self.env['res.partner'].search([
            ('is_student', '=', True),
            ('standard', '!=', False),
        ])
        grouped = {}
        for student in students:
            key = (student.standard.id, student.curr_year.id, student.div.id)
            grouped[key] = grouped.get(key, self.env['res.partner']) | student
        for peers in grouped.values():
            ranked = peers.sorted(key=lambda student: student.student_result or 0.0, reverse=True)
            for index, student in enumerate(ranked, start=1):
                student.student_rank = index
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Student Ranks'),
                'message': _('Ranks were updated from Result Percentage for each standard, year and division.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def update_student_percentage(self):
        Result = self.env['student.result'] if 'student.result' in self.env else False
        if Result:
            result_records = Result.search([
                ('student_id', 'in', self.ids),
                ('is_result_annual', '=', True),
            ])
            if result_records and hasattr(result_records, 'calculate_student_percentage'):
                result_records.calculate_student_percentage()
                return True
        raise UserError(_(
            "Enter Result Percentage on the student form. "
            "Exam result records (student.result) are not available in this database."
        ))

    @api.model
    def _get_grace_period(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('fees.no_of_days', default=3))

    def check_fees_and_cancel_admission(self):
        grace_period_days = self._get_grace_period()
        current_date = fields.Datetime.now()

        confirmed_students = self.env['res.partner'].search([
            ('is_student', '=', True),
            ('state', '=', 'confirm'),
            ('admission_date', '<=', current_date - timedelta(days=grace_period_days)),
        ])

        Fees = self.env['fees.fees'] if 'fees.fees' in self.env else False
        for student in confirmed_students:
            fees_paid = Fees.search_count([
                ('student', '=', student.id),
                ('payment_state', '=', 'paid'),
            ]) if Fees else 0
            if fees_paid == 0:
                student.cancel_state()

    def confirm_student(self):
        for rec in self:
            rec.state = 'confirm'
            rec.standard._compute_occupied_seats()
            rec.standard._compute_available_seats()

            if rec.applied_from_website:
                fees = rec._get_standard_fee()
                invite_template = rec.env.ref('jt_education_base.admission_successfull_template1')
                invite_template.with_context(fees=fees).send_mail(
                    rec.id,
                    force_send=True,
                    email_values={
                        'email_from': rec.env.user.email_formatted,
                        'email_to': rec.email,
                        'subject': 'Admission confirmation',
                    },
                )

    def pending_fees(self):
        partners = self.env['res.partner'].search([
            ('applied_from_website', '=', True),
            ('admission_date', '!=', False),
        ])

        for partner in partners:
            if partner.admission_date and partner.curr_year:
                curr_year_str = (partner.curr_year.name or '').strip()
                try:
                    year_range = curr_year_str.split('-')
                    start_year = int(year_range[0])
                    admission_year = partner.admission_date.year
                    if start_year == admission_year:
                        if partner.standard.app_close_date and partner.standard.app_close_date < date.today():
                            fee_record = (
                                self.env['fees.fees'].search([('student', '=', partner.id)], limit=1)
                                if 'fees.fees' in self.env else False
                            )
                            if not fee_record:
                                template = self.env.ref('jt_education_base.admission_pending_fees_template')
                                template.with_context(fees=partner._get_standard_fee()).send_mail(
                                    partner.id,
                                    force_send=True,
                                    email_values={
                                        'email_from': self.env.user.email_formatted,
                                        'email_to': partner.email,
                                        'subject': 'Fee Payment Reminder',
                                    },
                                )
                except (ValueError, IndexError, AttributeError):
                    continue

    def cancel_state(self):
        self.state = 'cancel'
        if self.standard:
            self.standard.occupied_seats -= 1
            self.standard.vacant_seates += 1
            invite_template = self.env.ref('jt_education_base.admission_cancel_template')
            invite_template.send_mail(
                self.id,
                force_send=True,
                email_values={
                    'email_from': self.env.user.email_formatted,
                    'email_to': self.email,
                    'subject': 'Admission Status Information',
                },
            )

    def _get_standard_fee(self):
        self.ensure_one()
        if not self.standard:
            return 0.0
        return self.standard.fee or 0.0

    def send_by_mail(self):
        for student in self:
            if not student.email:
                raise UserError(_("Student %s has no email address.", student.display_name))
            invite_template = student.env.ref('jt_education_base.send_by_mail_template_remainder4')
            invite_template.with_context(fees=student._get_standard_fee()).send_mail(
                student.id,
                force_send=True,
                email_values={
                    'email_from': student.env.user.email_formatted,
                    'email_to': student.email,
                    'subject': 'Fees Reminder',
                },
            )

    def open_wizard_academic_year(self):
        self.ensure_one()
        return self.env['ir.actions.act_window']._for_xml_id(
            'jt_education_base.action_change_acedamic_year'
        )

    @api.onchange('studend_type')
    def student_chng_type(self):
        self.company_type = self.studend_type

    def get_days_in_month(self, month, year):
        if month == 2:
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return 29
            return 28
        if month in [4, 6, 9, 11]:
            return 30
        return 31

    @api.depends('birthdate')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.birthdate:
                rec.age = today.year - rec.birthdate.year - (
                    (today.month, today.day) < (rec.birthdate.month, rec.birthdate.day)
                )
                years = today.year - rec.birthdate.year
                months = today.month - rec.birthdate.month
                days = today.day - rec.birthdate.day
                if days < 0:
                    months -= 1
                    days += rec.get_days_in_month(rec.birthdate.month, rec.birthdate.year)
                if months < 0:
                    years -= 1
                    months += 12
                rec.detailed_age = "%s  Years  %s  Months  %s  Days  " % (years, months, days)
            else:
                rec.age = 0
                rec.detailed_age = False

    @api.constrains('birthdate')
    def validation_constraints(self):
        today = fields.Date.today()
        for rec in self:
            if rec.birthdate and rec.birthdate >= today:
                raise exceptions.ValidationError(_('Invalid date of birth ..please enter correct date'))

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            if partner.company_type == 'student' or partner.is_student:
                if not partner.stud_id:
                    partner.stud_id = self.env['ir.sequence'].next_by_code('studentinformation.seq')
        return partners

    def get_roll_no(self):
        for record in self:
            if not record.roll_no:
                last_roll = self.search([
                    ('standard', '=', record.standard.id),
                    ('div', '=', record.div.id),
                    ('roll_no', '!=', False),
                ], order='roll_no desc', limit=1)
                record.roll_no = int(last_roll.roll_no) + 1 if last_roll else 1
            else:
                raise ValidationError(_("Roll number already generated for this record."))

    @api.onchange('is_student')
    def onchange_company_type1(self):
        super().onchange_company_type()
        if self.is_student:
            self.company_type = 'student'

    def _compute_company_type(self):
        for partner in self:
            if partner.is_student:
                partner.company_type = 'student'
            elif partner.is_company:
                partner.company_type = 'company'
            else:
                partner.company_type = 'person'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('is_student'):
            res['is_student'] = True
        return res


class StudentStandard(models.Model):
    _name = 'student.standard'
    _description = 'Student Standard'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Standard')
    capacity = fields.Integer("Capacity")
    occupied_seats = fields.Integer("Occupied Seats")
    vacant_seates = fields.Integer("Seats Available")
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    fee = fields.Monetary(string='Fee', currency_field='currency_id')
    student_ids = fields.One2many('res.partner', 'standard', string="Students", domain=[('is_student', '=', True)])
    app_close_date = fields.Date("Application Close Date")

    def _compute_occupied_seats(self):
        for standard in self:
            standard.occupied_seats = self.env['res.partner'].search_count([
                ('standard', '=', standard.id),
                ('is_student', '=', True),
                ('state', '=', 'confirm'),
            ])

    def _compute_available_seats(self):
        for standard in self:
            standard.vacant_seates = standard.capacity - standard.occupied_seats


class HowKnow(models.Model):
    _name = 'how.know'
    _description = 'How Know'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')


class StandardDivision(models.Model):
    _name = 'standard.division'
    _description = 'Standard Division'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Division')
    capacity = fields.Integer("Capacity")
    occupied_seats = fields.Integer("Occupied Seats", compute='_compute_occupied_seats', store=True)
    vacant_seates = fields.Integer("Seats Available", compute='_compute_available_seats', store=True)
    standard_id = fields.Many2one('student.standard', string='Standard')

    @api.depends('standard_id')
    def _compute_occupied_seats(self):
        for division in self:
            division.occupied_seats = self.env['res.partner'].search_count([
                ('div', '=', division.id),
                ('standard', '=', division.standard_id.id),
                ('is_student', '=', True),
            ])

    @api.depends('occupied_seats', 'capacity')
    def _compute_available_seats(self):
        for division in self:
            division.vacant_seates = division.capacity - division.occupied_seats


class Year(models.Model):
    _name = 'year.year'
    _description = 'Year'

    name = fields.Char('Year')


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_student = fields.Boolean(string='Is Student', compute='_compute_is_student_and_is_parent')
    is_parent = fields.Boolean(string='Is Parent', compute='_compute_is_student_and_is_parent')

    @api.depends('partner_id', 'partner_id.is_student', 'partner_id.is_parent')
    def _compute_is_student_and_is_parent(self):
        for user in self:
            user.is_student = bool(user.partner_id.is_student)
            user.is_parent = bool(user.partner_id.is_parent)


class StudentHistory(models.Model):
    _name = 'student.history'
    _description = 'Student History'

    student_id = fields.Many2one("res.partner", string="Student")
    year_changed_from = fields.Many2one('year.year', string="Changed Academic Year From", help="Previous academic year")
    year_changed_to = fields.Many2one('year.year', string="Changed Academic Year To", help="New academic year")
    reason = fields.Char("Reason")
