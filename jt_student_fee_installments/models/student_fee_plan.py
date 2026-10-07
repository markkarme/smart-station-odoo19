# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StudentFeePlan(models.Model):
    _name = 'student.fee.plan'
    _description = 'Student Fee Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year_id desc, student_id'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Reference',
        copy=False,
        default=lambda self: _('New'),
        tracking=True,
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    student_id = fields.Many2one(
        'res.partner',
        string='Student / اسم الطالب',
        required=True,
        domain=[('is_student', '=', True)],
        tracking=True,
        index=True,
        ondelete='restrict',
    )
    year_id = fields.Many2one(
        'year.year',
        string='Academic Year',
        required=True,
        tracking=True,
        index=True,
        ondelete='restrict',
    )
    standard_id = fields.Many2one('student.standard', string='Standard', tracking=True)
    division_id = fields.Many2one('standard.division', string='Division')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('closed', 'Closed'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )
    note = fields.Text(string='Notes')

    # --- Basic expense installments ---
    basic_installment_count = fields.Integer(
        string='Number of Basic Installments / عدد أقساط المصاريف',
        default=3,
        tracking=True,
    )
    basic_total_due = fields.Monetary(
        string='Total Basic Dues / اجمالي المصاريف الأساسية',
        currency_field='currency_id',
        tracking=True,
    )
    basic_installment_ids = fields.One2many(
        'student.fee.installment',
        'plan_id',
        string='Basic Installments',
        domain=[('fee_type', '=', 'basic')],
        context={'default_fee_type': 'basic'},
    )
    basic_paid = fields.Monetary(
        string='Basic Paid',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )
    basic_remaining = fields.Monetary(
        string='Basic Remaining',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    # --- Bus installments ---
    bus_installment_count = fields.Integer(
        string='Number of Bus Installments / عدد أقساط الباصات',
        default=2,
        tracking=True,
    )
    bus_total_due = fields.Monetary(
        string='Total Bus Dues / اجمالي الباصات',
        currency_field='currency_id',
        tracking=True,
    )
    bus_installment_ids = fields.One2many(
        'student.fee.installment',
        'plan_id',
        string='Bus Installments',
        domain=[('fee_type', '=', 'bus')],
        context={'default_fee_type': 'bus'},
    )
    bus_paid = fields.Monetary(
        string='Bus Paid',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )
    bus_remaining = fields.Monetary(
        string='Bus Remaining',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    # --- Other fees (non-installment) ---
    books_fee_ids = fields.One2many(
        'student.fee.other',
        'plan_id',
        string='الكتب',
        domain=[('fee_type', '=', 'books')],
        context={'default_fee_type': 'books'},
    )
    uniform_fee_ids = fields.One2many(
        'student.fee.other',
        'plan_id',
        string='اليونيفورم',
        domain=[('fee_type', '=', 'uniform')],
        context={'default_fee_type': 'uniform'},
    )
    books_paid = fields.Monetary(
        string='Books Paid',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )
    uniform_paid = fields.Monetary(
        string='Uniform Paid',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    installment_ids = fields.One2many(
        'student.fee.installment',
        'plan_id',
        string='All Installments',
    )
    other_fee_ids = fields.One2many(
        'student.fee.other',
        'plan_id',
        string='All Other Fees',
    )

    total_due = fields.Monetary(
        string='Total Dues / اجمالي المستحقات',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )
    total_paid = fields.Monetary(
        string='Total Paid / اجمالي السداد',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )
    remaining = fields.Monetary(
        string='Remaining / المتبقي',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    _sql_constraints = [
        (
            'student_year_uniq',
            'unique(student_id, year_id, company_id)',
            'A fee plan already exists for this student and academic year.',
        ),
    ]

    @api.depends('student_id.name', 'year_id.name', 'name')
    def _compute_display_name(self):
        for plan in self:
            student = plan.student_id.name or ''
            year = plan.year_id.name or ''
            plan.display_name = (
                f'{student} — {year}' if student or year else (plan.name or _('Fee Plan'))
            )

    @api.depends(
        'basic_total_due',
        'bus_total_due',
        'installment_ids.amount_paid',
        'installment_ids.fee_type',
        'other_fee_ids.amount',
        'other_fee_ids.fee_type',
        'other_fee_ids.is_paid',
    )
    def _compute_totals(self):
        for plan in self:
            basic_paid = sum(
                plan.installment_ids.filtered(lambda l: l.fee_type == 'basic').mapped('amount_paid')
            )
            bus_paid = sum(
                plan.installment_ids.filtered(lambda l: l.fee_type == 'bus').mapped('amount_paid')
            )
            books_lines = plan.other_fee_ids.filtered(lambda l: l.fee_type == 'books')
            uniform_lines = plan.other_fee_ids.filtered(lambda l: l.fee_type == 'uniform')
            books_total = sum(books_lines.mapped('amount'))
            uniform_total = sum(uniform_lines.mapped('amount'))
            # Paid summary: only lines whose invoice is paid (is_paid)
            books_paid = sum(books_lines.filtered('is_paid').mapped('amount'))
            uniform_paid = sum(uniform_lines.filtered('is_paid').mapped('amount'))
            plan.basic_paid = basic_paid
            plan.bus_paid = bus_paid
            plan.books_paid = books_paid
            plan.uniform_paid = uniform_paid
            plan.basic_remaining = (plan.basic_total_due or 0.0) - basic_paid
            plan.bus_remaining = (plan.bus_total_due or 0.0) - bus_paid
            # Total dues include books/uniform whether paid or not
            plan.total_due = (
                (plan.basic_total_due or 0.0)
                + (plan.bus_total_due or 0.0)
                + books_total
                + uniform_total
            )
            plan.total_paid = basic_paid + bus_paid + books_paid + uniform_paid
            plan.remaining = plan.total_due - plan.total_paid

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if not self.student_id:
            return
        self.year_id = self.student_id.curr_year
        self.standard_id = self.student_id.standard
        self.division_id = self.student_id.div
        if self.student_id.standard and self.student_id.standard.fee and not self.basic_total_due:
            self.basic_total_due = self.student_id.standard.fee

    def _split_amount(self, total, count):
        """Split total across count installments (last line gets remainder)."""
        if count <= 0:
            return []
        total = total or 0.0
        base = round(total / count, 2)
        amounts = [base] * count
        amounts[-1] = round(total - base * (count - 1), 2)
        return amounts

    def _sync_installment_lines(self, fee_type, count, total_due):
        """Create/update/remove installment lines for a fee type."""
        self.ensure_one()
        Installment = self.env['student.fee.installment']
        existing = Installment.search([
            ('plan_id', '=', self.id),
            ('fee_type', '=', fee_type),
        ], order='number')
        count = max(int(count or 0), 0)
        amounts = self._split_amount(total_due, count) if count else []

        # Remove extra lines (only unpaid empty ones preferred; force remove extras)
        for line in existing.filtered(lambda l: l.number > count):
            line.unlink()

        existing = Installment.search([
            ('plan_id', '=', self.id),
            ('fee_type', '=', fee_type),
        ], order='number')
        by_number = {line.number: line for line in existing}

        for number in range(1, count + 1):
            amount_due = amounts[number - 1] if number <= len(amounts) else 0.0
            line = by_number.get(number)
            if line:
                # Keep paid amount/receipt; refresh due if not fully customized mid-payment
                line.write({'amount_due': amount_due})
            else:
                Installment.create({
                    'plan_id': self.id,
                    'fee_type': fee_type,
                    'number': number,
                    'amount_due': amount_due,
                })

    def action_generate_installments(self):
        """Generate / refresh installment lines from counts and totals."""
        for plan in self:
            if plan.basic_installment_count < 0 or plan.bus_installment_count < 0:
                raise ValidationError(_('Installment count cannot be negative.'))
            plan._sync_installment_lines(
                'basic',
                plan.basic_installment_count,
                plan.basic_total_due,
            )
            plan._sync_installment_lines(
                'bus',
                plan.bus_installment_count,
                plan.bus_total_due,
            )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                student = self.env['res.partner'].browse(vals.get('student_id'))
                year = self.env['year.year'].browse(vals.get('year_id'))
                vals['name'] = '%s / %s' % (
                    student.name or _('Student'),
                    year.name or _('Year'),
                )
            if not vals.get('standard_id') and vals.get('student_id'):
                student = self.env['res.partner'].browse(vals['student_id'])
                vals.setdefault('standard_id', student.standard.id or False)
                vals.setdefault('division_id', student.div.id or False)
                if not vals.get('basic_total_due') and student.standard:
                    vals['basic_total_due'] = student.standard.fee or 0.0
        plans = super().create(vals_list)
        plans.action_generate_installments()
        return plans

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_installment_sync'):
            return res
        sync_fields = {
            'basic_installment_count',
            'bus_installment_count',
            'basic_total_due',
            'bus_total_due',
        }
        if sync_fields & set(vals):
            self.action_generate_installments()
        return res

    def action_open(self):
        self.write({'state': 'open'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_draft(self):
        self.write({'state': 'draft'})

    @api.constrains('basic_installment_count', 'bus_installment_count')
    def _check_counts(self):
        for plan in self:
            if plan.basic_installment_count < 0 or plan.bus_installment_count < 0:
                raise ValidationError(_('Installment count cannot be negative.'))
            if plan.basic_total_due < 0 or plan.bus_total_due < 0:
                raise ValidationError(_('Total dues cannot be negative.'))
