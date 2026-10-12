# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GenerateFeePlansWizard(models.TransientModel):
    _name = 'generate.fee.plans.wizard'
    _description = 'Generate Student Fee Plans'

    year_id = fields.Many2one('year.year', string='العام الدراسي', required=True)
    standard_id = fields.Many2one(
        'student.standard',
        string='الصف (تصفية اختيارية)',
    )
    basic_installment_count = fields.Integer(
        string='أقساط المصاريف الدراسية',
        default=3,
    )
    bus_installment_count = fields.Integer(
        string='أقساط الباصات',
        default=2,
    )
    default_basic_total_due = fields.Float(
        string='إجمالي المصاريف الدراسية الافتراضي',
        help='Used when the student standard has no fee amount.',
    )
    bus_category_id = fields.Many2one(
        'bus.category',
        string='فئة الباص',
        help='Default bus when the student has no bus assigned. Price fills bus total.',
    )
    default_bus_total_due = fields.Float(string='إجمالي الباصات الافتراضي')
    default_books_amount = fields.Float(
        string='سعر الكتب',
        help='Creates a books fee line on each generated / updated plan.',
    )
    overwrite_due = fields.Boolean(
        string='تحديث الإجماليات / الأعداد في الخطط الموجودة',
        default=False,
    )
    student_count = fields.Integer(
        string='الطلاب الموجودون',
        compute='_compute_student_count',
    )

    @api.depends('year_id', 'standard_id')
    def _compute_student_count(self):
        Partner = self.env['res.partner']
        for wizard in self:
            domain = [('is_student', '=', True)]
            if wizard.year_id:
                domain.append(('curr_year', '=', wizard.year_id.id))
            if wizard.standard_id:
                domain.append(('standard', '=', wizard.standard_id.id))
            wizard.student_count = Partner.search_count(domain) if wizard.year_id else 0

    @api.onchange('standard_id')
    def _onchange_standard_id(self):
        if self.standard_id and self.standard_id.fee:
            self.default_basic_total_due = self.standard_id.fee

    @api.onchange('bus_category_id')
    def _onchange_bus_category_id(self):
        if self.bus_category_id:
            self.default_bus_total_due = self.bus_category_id.price or 0.0

    def _resolve_bus(self, student):
        """Student bus first, else wizard bus category."""
        self.ensure_one()
        bus = student.bus_category_id or self.bus_category_id
        if bus:
            return bus, bus.price or 0.0
        return self.env['bus.category'], self.default_bus_total_due or 0.0

    def _ensure_books_line(self, plan, amount):
        """Create or update a single unpaid books line with the given amount."""
        if not amount:
            return
        Other = self.env['student.fee.other']
        line = Other.search([
            ('plan_id', '=', plan.id),
            ('fee_type', '=', 'books'),
        ], limit=1)
        vals = {
            'amount': amount,
            'payment_date': False,
        }
        if line:
            if self.overwrite_due or not line.amount:
                line.write(vals)
        else:
            Other.create({
                'plan_id': plan.id,
                'fee_type': 'books',
                **vals,
            })

    def action_generate(self):
        self.ensure_one()
        domain = [
            ('is_student', '=', True),
            ('curr_year', '=', self.year_id.id),
        ]
        if self.standard_id:
            domain.append(('standard', '=', self.standard_id.id))

        students = self.env['res.partner'].search(domain)
        if not students:
            raise UserError(_('No students found for the selected year/standard.'))

        Plan = self.env['student.fee.plan']
        created = 0
        updated = 0
        books_amount = self.default_books_amount or 0.0

        for student in students:
            plan = Plan.search([
                ('student_id', '=', student.id),
                ('year_id', '=', self.year_id.id),
            ], limit=1)
            basic_due = (
                student.standard.fee
                if student.standard and student.standard.fee
                else self.default_basic_total_due
            )
            bus, bus_due = self._resolve_bus(student)
            vals = {
                'standard_id': student.standard.id,
                'division_id': student.div.id,
                'class_id': student.class_id.id,
                'bus_category_id': bus.id if bus else False,
                'basic_installment_count': self.basic_installment_count,
                'bus_installment_count': self.bus_installment_count,
                'basic_total_due': basic_due or 0.0,
                'bus_total_due': bus_due,
                'state': 'draft',
            }
            if plan:
                if self.overwrite_due:
                    plan.write(vals)
                else:
                    plan.write({
                        'standard_id': student.standard.id,
                        'division_id': student.div.id,
                        'class_id': student.class_id.id,
                        'bus_category_id': bus.id if bus else plan.bus_category_id.id,
                    })
                self._ensure_books_line(plan, books_amount)
                updated += 1
            else:
                plan = Plan.create({
                    'student_id': student.id,
                    'year_id': self.year_id.id,
                    **vals,
                })
                self._ensure_books_line(plan, books_amount)
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fee Plans'),
                'message': _(
                    'Created %(created)s plan(s), updated %(updated)s existing plan(s).',
                    created=created,
                    updated=updated,
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
