# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, formatLang


class ResPartner(models.Model):
    _inherit = 'res.partner'

    bus_category_id = fields.Many2one(
        'bus.category',
        string='الباص',
        help='Bus category assigned to this student.',
    )
    fee_plan_ids = fields.One2many(
        'student.fee.plan',
        'student_id',
        string='Fee Plans',
    )
    fee_plan_count = fields.Integer(
        string='Installments',
        compute='_compute_fee_plan_count',
    )

    def _compute_fee_plan_count(self):
        Plan = self.env['student.fee.plan']
        for partner in self:
            partner.fee_plan_count = Plan.search_count([
                ('student_id', '=', partner.id),
            ]) if partner.is_student else 0

    def _get_current_fee_plan(self):
        """Return the open/draft fee plan for the current academic year, else latest."""
        self.ensure_one()
        Plan = self.env['student.fee.plan']
        domain = [
            ('student_id', '=', self.id),
            ('state', '!=', 'closed'),
        ]
        if self.curr_year:
            plan = Plan.search(
                domain + [('year_id', '=', self.curr_year.id)],
                limit=1,
            )
            if plan:
                return plan
        return Plan.search(domain, order='year_id desc, id desc', limit=1)

    def _get_next_unpaid_installments(self):
        """Unpaid installment lines for the current fee plan, soonest due first."""
        self.ensure_one()
        plan = self._get_current_fee_plan()
        if not plan:
            return self.env['student.fee.installment']
        lines = plan.installment_ids.filtered(lambda l: not l.is_paid)
        has_due_date = 'due_date' in lines._fields
        if has_due_date:
            return lines.sorted(
                key=lambda l: (
                    l.due_date or fields.Date.to_date('9999-12-31'),
                    l.fee_type or '',
                    l.number or 0,
                )
            )
        return lines.sorted(key=lambda l: (l.fee_type or '', l.number or 0))

    def _prepare_fee_reminder_context(self):
        """Context for the installment fee reminder email."""
        self.ensure_one()
        lines = self._get_next_unpaid_installments()
        next_installments = []
        for line in lines:
            remaining = max((line.amount_due or 0.0) - (line.amount_paid or 0.0), 0.0)
            if remaining <= 0:
                continue
            due_date = line.due_date if 'due_date' in line._fields else False
            next_installments.append({
                'name': line.name or _('Installment %s') % (line.number or ''),
                'amount': remaining,
                'amount_display': formatLang(
                    self.env,
                    remaining,
                    currency_obj=line.currency_id,
                ),
                'due_date': due_date,
                'due_date_display': format_date(self.env, due_date) if due_date else False,
            })

        fees_total = sum(item['amount'] for item in next_installments)
        if not next_installments:
            plan = self._get_current_fee_plan()
            fees_total = plan.remaining if plan else self._get_standard_fee()

        return {
            'next_installments': next_installments,
            'fees': formatLang(
                self.env,
                fees_total,
                currency_obj=(
                    lines[:1].currency_id
                    if lines
                    else self.env.company.currency_id
                ),
            ),
        }

    def _get_fee_reminder_lang(self):
        """Always prefer Arabic for fee reminder emails."""
        self.ensure_one()
        lang = self.lang or self.env.user.lang or 'ar_001'
        if lang.startswith('ar'):
            return lang
        # Fallback to installed Arabic locale
        Lang = self.env['res.lang'].sudo()
        for code in ('ar_001', 'ar'):
            if Lang.search([('code', '=', code), ('active', '=', True)], limit=1):
                return code
        return 'ar_001'

    def send_by_mail(self):
        """Fees Reminder: next unpaid installments with due dates (Arabic)."""
        template = self.env.ref(
            'jt_student_fee_installments.mail_template_fee_installment_reminder'
        )
        for student in self:
            if not student.email:
                raise UserError(_("Student %s has no email address.", student.display_name))
            lang = student._get_fee_reminder_lang()
            lang_student = student.with_context(lang=lang)
            template.with_context(
                lang=lang,
                **lang_student._prepare_fee_reminder_context()
            ).send_mail(
                student.id,
                force_send=True,
                email_values={
                    'email_from': student.env.user.email_formatted,
                    'email_to': student.email,
                    'subject': 'تذكير بالرسوم',
                },
            )

    def action_view_fee_plans(self):
        """Quick access to this student's installment fee plan(s)."""
        self.ensure_one()
        context = {
            'default_student_id': self.id,
            'default_year_id': self.curr_year.id if self.curr_year else False,
            'default_standard_id': self.standard.id if self.standard else False,
            'default_division_id': self.div.id if self.div else False,
            'default_class_id': self.class_id.id if self.class_id else False,
            'default_bus_category_id': self.bus_category_id.id if self.bus_category_id else False,
            'default_basic_total_due': self.standard.fee if self.standard else 0.0,
            'default_bus_total_due': self.bus_category_id.price if self.bus_category_id else 0.0,
            'default_state': 'open',
        }
        plans = self.env['student.fee.plan'].search([
            ('student_id', '=', self.id),
        ])

        action = {
            'name': _('Installments'),
            'type': 'ir.actions.act_window',
            'res_model': 'student.fee.plan',
            'domain': [('student_id', '=', self.id)],
            'context': context,
            'target': 'current',
        }

        if len(plans) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': plans.id,
            })
        elif not plans:
            # Open a new fee plan form prefilled for this student
            action.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
            })
        else:
            action['view_mode'] = 'list,form'

        return action
