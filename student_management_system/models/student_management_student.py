from odoo import models, fields, api, Command
from odoo.exceptions import UserError


class Student(models.Model):
    _name = 'student.management.student'
    _description = 'Student Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Student Name', required=True)
    icon = fields.Image(string="Photo")
    contact_info = fields.Char(string='Contact Info')
    NRC = fields.Char(string="NRC")
    course_id = fields.Many2one('student.management.course', string='Course', required=True)
    fee = fields.Monetary(related='course_id.fee', string='Fee', readonly=True, currency_field='currency_id', store=True)
    branch = fields.Many2one(related='course_id.branch_id', string='Branch', readonly=True, store=True)
    teacher = fields.Many2one(related='course_id.teacher_id', string='Teacher', readonly=True, store=True)
    duration = fields.Char(related='course_id.duration', string='Duration', readonly=True)
    teacher_schedule = fields.Text(string="Teacher's Schedule", compute='_compute_teacher_schedule')
    discount = fields.Float('Discount-%')
    discount_reason = fields.Char("Discount Reason")
    discount_amount = fields.Float("Discount Amount")
    final_fee = fields.Monetary(string='Final Fee', compute='_compute_final_fee', store=True, currency_field='currency_id')
    is_ncc = fields.Boolean(string="Is NCC", tracking=True)
    exam_fee_course = fields.Many2one('student.management.course', string='Exam Fee Course', store=True, tracking=True)
    exam_fee = fields.Monetary(string='Exam Fee', currency_field='currency_id', store=True, tracking=True)
    reg_fee_course = fields.Many2one('student.management.course', string='Register Fee Course', store=True, tracking=True)
    reg_fee = fields.Monetary(string='Register Fee', currency_field='currency_id', store=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
        readonly=True,
    )
    active = fields.Boolean(default=True)
    where_about_know = fields.Selection([
        ('facebook', 'Facebook'),
        ('tiktok', 'TikTok'),
        ('linkedin', 'LinkedIn'),
        ('friend', 'From a Friend'),
        ('website', 'University Website'),
        ('other', 'Other'),
    ], string='How did you hear about us?', default='facebook', required=True)
    room_id = fields.Many2one('student.management.room', string='Room', store=True)
    sequence_code = fields.Char(string='Student Code', required=True, copy=False, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('admission', 'Admission'),
        ('invoice', 'Invoice'),
        ('certificate', 'Complete'),
    ], default='draft', string="Student State", tracking=True)
    parent = fields.Char(string="Parent Name")
    dob = fields.Date(string="Date of Birth")
    mobile = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], default='male', string='Gender')
    blood_group = fields.Selection([
        ('a+', 'A+'),
        ('a-', 'A-'),
        ('b+', 'B+'),
        ('b-', 'B-'),
        ('ab+', 'AB+'),
        ('ab-', 'AB-'),
        ('o+', 'O+'),
        ('o-', 'O-'),
    ], string='Blood Group')
    address = fields.Char(string='Address')
    invoice_count = fields.Integer(string='Invoices', compute='_compute_invoice_count')
    invoice_status_clone = fields.Selection([
        ('paid', 'Fully Paid'),
        ('partical', 'Partical Paid'),
    ])
    invoice_status = fields.Char(compute='_compute_invoice_status', string="Invoice Status")
    last_amount_paid_fee = fields.Monetary(
        compute='_compute_last_amount_paid_fee',
        string="Last Amount Paid",
        currency_field='currency_id',
    )
    switch_course = fields.Char(string="Course Change  Reason", tracking=True)
    related_teacher_ids = fields.Many2many(
        'student.management.teacher',
        string='Related Teachers',
        compute='_compute_related_teachers',
        store=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence_code') or vals.get('sequence_code') == 'New':
                vals['sequence_code'] = self.env['ir.sequence'].next_by_code('student.management.student') or 'New'
        return super().create(vals_list)

    def _get_or_create_partner(self):
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        partner = self.env['res.partner'].search([('name', '=', self.name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.name,
                'email': self.email,
                'phone': self.mobile,
            })
        self.partner_id = partner
        return partner

    def _get_income_account(self):
        account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', self.env.company.id),
        ], limit=1)
        if not account:
            account = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
        if not account:
            raise UserError("No income account was found. Please configure an Income account first.")
        return account

    def _has_student_code(self):
        self.ensure_one()
        return bool(self.sequence_code) and self.sequence_code != 'New'

    def _student_invoice_domain(self):
        self.ensure_one()
        if not self._has_student_code():
            return [('id', '=', False)]
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('payment_reference', '=', self.sequence_code),
        ]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        elif self.name:
            domain.append(('partner_id.name', '=', self.name))
        else:
            return [('id', '=', False)]
        return domain

    @api.onchange('exam_fee_course', 'reg_fee_course')
    def _onchange_fees(self):
        if self.exam_fee_course:
            self.exam_fee = self.exam_fee_course.fee
        if self.reg_fee_course:
            self.reg_fee = self.reg_fee_course.fee

    def action_add_fee(self):
        for student in self:
            invoice = self.env['account.move'].search(student._student_invoice_domain(), limit=1)
            if not invoice:
                continue
            if invoice.state != 'draft':
                raise UserError("Invoice %s is not in draft. Reset it to draft before adding fees." % invoice.name)
            account = student._get_income_account()
            for course, fee in [(student.exam_fee_course, student.exam_fee), (student.reg_fee_course, student.reg_fee)]:
                if not course:
                    continue
                matched_line = invoice.invoice_line_ids.filtered(lambda line: line.name == course.name)
                if matched_line:
                    matched_line.write({'price_unit': fee})
                else:
                    invoice.write({
                        'invoice_line_ids': [Command.create({
                            'name': course.name,
                            'quantity': 1,
                            'price_unit': fee,
                            'account_id': account.id,
                            'display_type': 'product',
                        })],
                    })

    @api.onchange('discount')
    def _onchange_discount(self):
        for record in self:
            if record.course_id.fee:
                record.discount_amount = record.course_id.fee * (record.discount / 100)
            else:
                record.discount_amount = 0.0

    @api.onchange('discount_amount')
    def _onchange_discount_amount(self):
        for record in self:
            if record.course_id.fee:
                record.discount = (record.discount_amount / record.course_id.fee) * 100
            else:
                record.discount = 0.0

    @api.depends('course_id.fee', 'exam_fee', 'reg_fee', 'discount_amount')
    def _compute_final_fee(self):
        for record in self:
            record.final_fee = ((record.exam_fee or 0.0) + (record.reg_fee or 0.0) + (record.course_id.fee or 0.0)) - (record.discount_amount or 0.0)

    @api.depends('course_id.teacher_id', 'course_id.schedule_ids')
    def _compute_teacher_schedule(self):
        for student in self:
            schedule_details = []
            if student.course_id and student.course_id.schedule_ids:
                for schedule in student.course_id.schedule_ids:
                    formatted_schedule = "%s: %s:00 - %s:00" % (
                        dict(schedule._fields['day'].selection).get(schedule.day),
                        int(schedule.start_time),
                        int(schedule.end_time),
                    )
                    schedule_details.append(formatted_schedule)
            student.teacher_schedule = '\n'.join(schedule_details)

    @api.onchange('course_id')
    def _onchange_course_id(self):
        if self.course_id:
            branch_rooms = self.course_id.branch_id.room_ids
            self.room_id = branch_rooms[:1]
        else:
            self.room_id = False

    def set_admission(self):
        self.state = 'admission'

    def set_invoice(self):
        account = self._get_income_account()
        invoice = False
        for student in self:
            partner = student._get_or_create_partner()
            invoice = self.env['account.move'].create({
                'partner_id': partner.id,
                'move_type': 'out_invoice',
                'invoice_line_ids': [Command.create({
                    'name': student.course_id.name,
                    'quantity': 1,
                    'discount': student.discount,
                    'price_unit': student.fee,
                    'account_id': account.id,
                    'display_type': 'product',
                })],
                'payment_reference': student.sequence_code,
            })
            student.state = 'invoice'
        if invoice:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoice.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def set_certificate(self):
        self.state = 'certificate'

    @api.depends('name', 'partner_id', 'sequence_code')
    def _compute_invoice_count(self):
        for student in self:
            student.invoice_count = self.env['account.move'].search_count(student._student_invoice_domain())

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': self._student_invoice_domain(),
            'context': dict(self._context, create=False),
        }

    @api.depends('sequence_code', 'name', 'partner_id', 'final_fee')
    def _compute_invoice_status(self):
        for student in self:
            if not student._has_student_code():
                student.invoice_status = "No Payment"
                continue
            invoices = self.env['account.move'].search(student._student_invoice_domain())
            payments = invoices.matched_payment_ids | invoices.reconciled_payment_ids
            confirmed_payments = payments.filtered(lambda payment: payment.state in ('paid', 'in_process', 'posted'))
            total_paid = sum(confirmed_payments.mapped('amount'))
            total_amount = student.final_fee or 0.0
            if not invoices or not confirmed_payments:
                student.invoice_status = "No Payment" if not invoices else "Not Paid"
            elif total_paid == 0.0:
                student.invoice_status = "Not Paid"
            elif total_paid > 0.0 and total_paid < total_amount:
                partial_count = len(confirmed_payments)
                if partial_count == 1:
                    student.invoice_status = "Partially Paid (One Time)"
                elif partial_count == 2:
                    student.invoice_status = "Partially Paid (Two Times)"
                else:
                    student.invoice_status = "Partially Paid (%s Times)" % partial_count
            elif total_paid >= total_amount:
                student.invoice_status = "Paid"
            else:
                student.invoice_status = "Unknown Status"

    @api.depends('sequence_code', 'course_id', 'name', 'partner_id')
    def _compute_last_amount_paid_fee(self):
        for student in self:
            invoices = self.env['account.move'].search(
                student._student_invoice_domain(),
                order="invoice_date desc",
            )
            student.last_amount_paid_fee = invoices[:1].amount_residual_signed if invoices else 0.0

    def change_course(self):
        for student in self:
            if not student.switch_course or not student.switch_course.strip():
                raise UserError("Please provide a valid reason for changing the course. The reason cannot be empty or only spaces.")
            if student.invoice_count > 0:
                raise UserError("You cannot change the course because there are existing invoices linked to this student.")
        self.state = 'draft'

    @api.depends('course_id.teacher_id2')
    def _compute_related_teachers(self):
        for student in self:
            student.related_teacher_ids = student.course_id.teacher_id2
