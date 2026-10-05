# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

PENALTY_PRICE_PARAM = 'jt_student_fee_installments_exceptions_penalties.penalty_price_per_week'


class StudentFeePlan(models.Model):
    _inherit = 'student.fee.plan'

    penalty_price_per_week = fields.Float(
        string='Penalty per Week / غرامة الأسبوع',
        default=lambda self: float(
            self.env['ir.config_parameter'].sudo().get_param(PENALTY_PRICE_PARAM, '50')
        ),
        tracking=True,
        help='Amount charged for each week after the installment due date.',
    )
    installment_start_date = fields.Date(
        string='First Due Date',
        default=fields.Date.context_today,
        help='Due date of installment #1. Later installments use the interval below.',
    )
    installment_interval_months = fields.Integer(
        string='Months Between Due Dates',
        default=1,
        help='Gap between installment due dates (e.g. 1 = monthly).',
    )
    total_late_penalties = fields.Monetary(
        string='Total Late Penalties / اجمالي غرامات التأخير',
        currency_field='currency_id',
        compute='_compute_total_late_penalties',
    )
    exception_ids = fields.One2many(
        'student.fee.exception',
        'plan_id',
        string='Exceptions',
    )
    exception_count = fields.Integer(compute='_compute_exception_count')

    def _compute_exception_count(self):
        for plan in self:
            plan.exception_count = len(plan.exception_ids)

    @api.depends(
        'installment_ids.penalty_amount',
        'installment_ids.due_date',
        'installment_ids.is_paid',
        'installment_ids.payment_date',
        'installment_ids.penalty_waived',
        'penalty_price_per_week',
    )
    def _compute_total_late_penalties(self):
        for plan in self:
            plan.total_late_penalties = sum(plan.installment_ids.mapped('penalty_amount'))

    def _get_due_date_for_number(self, number):
        self.ensure_one()
        start = self.installment_start_date or fields.Date.context_today(self)
        months = max(self.installment_interval_months or 0, 0)
        if number <= 1:
            return start
        return start + relativedelta(months=months * (number - 1))

    def action_open_exception_wizard(self):
        self.ensure_one()
        if self.state == 'closed':
            raise UserError(_('You cannot create an exception on a closed fee plan.'))
        return {
            'name': _('Fee Exception'),
            'type': 'ir.actions.act_window',
            'res_model': 'student.fee.exception.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_plan_id': self.id,
            },
        }

    def action_view_exceptions(self):
        self.ensure_one()
        return {
            'name': _('Exceptions'),
            'type': 'ir.actions.act_window',
            'res_model': 'student.fee.exception',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }

    def action_apply_increase_installments(self, fee_type, new_count):
        """Increase installment count; keep paid lines, redistribute unpaid dues."""
        self.ensure_one()
        if fee_type not in ('basic', 'bus'):
            raise UserError(_('Invalid installment type.'))
        if new_count < 1:
            raise ValidationError(_('New installment count must be at least 1.'))

        lines = self.installment_ids.filtered(lambda l: l.fee_type == fee_type).sorted('number')
        paid_lines = lines.filtered('is_paid')
        unpaid_lines = lines - paid_lines
        current_count = len(lines)
        if new_count < current_count:
            raise UserError(_(
                'New count (%(new)s) cannot be lower than the current number of installments (%(cur)s). '
                'Use a higher number to increase installments.',
                new=new_count,
                cur=current_count,
            ))
        if new_count == current_count:
            raise UserError(_('New installment count is the same as the current count.'))
        if paid_lines and new_count < len(paid_lines):
            raise UserError(_('Cannot set fewer installments than already paid lines.'))

        total_field = 'basic_total_due' if fee_type == 'basic' else 'bus_total_due'
        count_field = 'basic_installment_count' if fee_type == 'basic' else 'bus_installment_count'
        total_due = self[total_field] or 0.0
        paid_due_sum = sum(paid_lines.mapped('amount_due'))
        unpaid_pool = max(total_due - paid_due_sum, 0.0)
        # Prefer redistributing current unpaid dues if totals drifted
        unpaid_pool = max(unpaid_pool, sum(unpaid_lines.mapped('amount_due')))

        # Create missing lines
        Installment = self.env['student.fee.installment']
        existing_numbers = set(lines.mapped('number'))
        for number in range(1, new_count + 1):
            if number not in existing_numbers:
                Installment.create({
                    'plan_id': self.id,
                    'fee_type': fee_type,
                    'number': number,
                    'amount_due': 0.0,
                    'due_date': self._get_due_date_for_number(number),
                })

        # Refresh unpaid set after create
        all_lines = self.installment_ids.filtered(lambda l: l.fee_type == fee_type).sorted('number')
        unpaid = all_lines.filtered(lambda l: not l.is_paid)
        amounts = self._split_amount(unpaid_pool, len(unpaid)) if unpaid else []
        for idx, line in enumerate(unpaid):
            vals = {'amount_due': amounts[idx] if idx < len(amounts) else 0.0}
            if not line.due_date:
                vals['due_date'] = self._get_due_date_for_number(line.number)
            if not line.amount_due_original:
                vals['amount_due_original'] = vals['amount_due']
            line.with_context(skip_original_due=True).write(vals)

        # Update count without triggering full regenerate overwrite
        self.with_context(skip_installment_sync=True).write({count_field: new_count})
        return True

    def action_apply_discount(self, installment_ids, discount_type, discount_value):
        """Apply fixed or percentage discount on selected unpaid installments."""
        self.ensure_one()
        lines = self.env['student.fee.installment'].browse(installment_ids).filtered(
            lambda l: l.plan_id == self and not l.is_paid
        )
        if not lines:
            raise UserError(_('Select at least one unpaid installment.'))
        if discount_value <= 0:
            raise ValidationError(_('Discount value must be greater than zero.'))

        if discount_type == 'percent':
            if discount_value > 100:
                raise ValidationError(_('Percentage discount cannot exceed 100%.'))
            for line in lines:
                original = line.amount_due_original or line.amount_due or 0.0
                if not line.amount_due_original:
                    line.amount_due_original = original
                new_due = round(original * (1 - discount_value / 100.0), 2)
                line.with_context(skip_original_due=True).write({'amount_due': max(new_due, 0.0)})
        elif discount_type == 'fixed':
            # Fixed amount is a total discount split equally across selected lines
            per_line = round(discount_value / len(lines), 2)
            remainder = round(discount_value - per_line * (len(lines) - 1), 2)
            for idx, line in enumerate(lines):
                cut = remainder if idx == len(lines) - 1 else per_line
                original = line.amount_due_original or line.amount_due or 0.0
                if not line.amount_due_original:
                    line.amount_due_original = original
                new_due = round(max((line.amount_due or 0.0) - cut, 0.0), 2)
                line.with_context(skip_original_due=True).write({'amount_due': new_due})
        else:
            raise UserError(_('Invalid discount type.'))
        return True

    def _assign_missing_due_dates(self):
        for plan in self:
            for line in plan.installment_ids.filtered(lambda l: not l.due_date):
                line.due_date = plan._get_due_date_for_number(line.number)

    @api.model_create_multi
    def create(self, vals_list):
        plans = super().create(vals_list)
        plans._assign_missing_due_dates()
        return plans

    def action_generate_installments(self):
        res = super().action_generate_installments()
        self._assign_missing_due_dates()
        return res
