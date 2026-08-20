from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PettyCashRequest(models.Model):
    _name = 'petty.cash.request'
    _description = 'Petty Cash Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _rec_name = 'name'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False,
        default='New', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
        tracking=True, default=lambda self: self.env.user.employee_id)
    fund_id = fields.Many2one('petty.cash.fund', string='Petty Cash Fund',
        domain="[('employee_id', '=', employee_id), ('state', '=', 'active')]", tracking=True)
    date = fields.Date(string='Request Date', required=True, default=fields.Date.today, tracking=True)
    requested_amount = fields.Monetary(
        string='Requested Amount', required=True, tracking=True,
        currency_field='currency_id',
    )
    amount = fields.Monetary(
        string='Approved Amount', tracking=True,
        currency_field='currency_id',
        help='Amount approved by the manager. Set on approval and used when marking as paid.',
    )
    amount_difference = fields.Monetary(
        string='Difference',
        compute='_compute_amount_difference',
        store=True,
        currency_field='currency_id',
        help='Requested amount minus approved amount.',
    )
    currency_id = fields.Many2one('res.currency', related='fund_id.currency_id', store=True)
    reason = fields.Text(string='Purpose / Reason', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By', tracking=True, readonly=True)
    approved_date = fields.Datetime(string='Approval Date', readonly=True)
    paid_date = fields.Date(string='Payment Date', readonly=True)
    company_id = fields.Many2one('res.company', related='fund_id.company_id', store=True)
    notes = fields.Text(string='Internal Notes')
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True)
    current_balance = fields.Monetary(related='fund_id.current_balance', string='Fund Balance',
        currency_field='currency_id')
    fund_move_count = fields.Integer(related='fund_id.move_count', string='Fund Journal Entries')
    can_edit_approved_amount = fields.Boolean(
        compute='_compute_can_edit_approved_amount',
    )

    @api.model
    def _user_can_edit_approved_amount(self):
        user = self.env.user
        if user.has_group('leapai_petty_cash.petty_cash_manager_group'):
            return True
        if not user.has_group('leapai_petty_cash.petty_cash_user_group'):
            return False
        for xmlid in ('purchase.group_purchase_manager', 'purchase.group_purchase_user'):
            if self.env.ref(xmlid, raise_if_not_found=False) and user.has_group(xmlid):
                return True
        return False

    @api.depends('state')
    def _compute_can_edit_approved_amount(self):
        allowed = self._user_can_edit_approved_amount()
        for rec in self:
            rec.can_edit_approved_amount = allowed and rec.state != 'paid'

    @api.depends('requested_amount', 'amount')
    def _compute_amount_difference(self):
        for rec in self:
            approved_amount = rec.amount or 0.0
            rec.amount_difference = rec.requested_amount - approved_amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.request') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.requested_amount <= 0:
                raise ValidationError(_('Requested amount must be greater than zero.'))
            if not rec.fund_id.journal_id:
                raise UserError(_('Please complete the fund setup first (create account and journal).'))
            rec.state = 'submitted'
            rec.message_post(body=_('Request submitted for approval.'))

    def action_approve(self):
        for rec in self:
            if not rec.amount:
                rec.amount = rec.requested_amount
            if rec.amount <= 0:
                raise ValidationError(_('Approved amount must be greater than zero.'))
            if rec.fund_id.current_balance < rec.amount:
                raise UserError(_(
                    'Insufficient balance in the petty cash fund.\nAvailable: %s, Approved: %s'
                ) % (rec.fund_id.current_balance, rec.amount))
            rec.state = 'approved'
            rec.approved_by = self.env.user
            rec.approved_date = fields.Datetime.now()
            rec.message_post(body=_(
                'Request approved by %s. Approved amount: %s (requested: %s).'
            ) % (self.env.user.name, rec.amount, rec.requested_amount))

    def action_mark_paid(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Approved amount must be greater than zero.'))
            if rec.fund_id.current_balance < rec.amount:
                raise UserError(_(
                    'Insufficient balance in the petty cash fund.\nAvailable: %s, Approved: %s'
                ) % (rec.fund_id.current_balance, rec.amount))
            existing_txn = self.env['petty.cash.transaction'].search([
                ('request_id', '=', rec.id),
            ], limit=1)
            if existing_txn:
                raise UserError(_('A transaction already exists for this request.'))
            self.env['petty.cash.transaction'].create({
                'fund_id': rec.fund_id.id,
                'date': rec.date,
                'description': f'[{rec.name}] {rec.reason[:50] if rec.reason else ""}',
                'credit': rec.amount,
                'debit': 0.0,
                'request_id': rec.id,
            })
            rec.state = 'paid'
            rec.paid_date = fields.Date.today()
            rec.message_post(body=_('Payment registered on %s for amount %s.') % (
                rec.paid_date, rec.amount))

    def action_reset_approved(self):
        """Reverse action_mark_paid: remove the payment transaction and return to approved."""
        for rec in self:
            if rec.state != 'paid':
                raise UserError(_('Only paid requests can be reset to approved.'))
            transactions = self.env['petty.cash.transaction'].search([
                ('request_id', '=', rec.id),
            ])
            fund = rec.fund_id
            for txn in transactions:
                move = txn.move_id
                if move and move.state == 'posted':
                    raise UserError(_(
                        'Cannot reset payment because journal entry %s is posted. '
                        'Reset the journal entry to draft first.'
                    ) % (move.name or move.display_name))
                draft_move = move if move and move.state == 'draft' else False
                txn.unlink()
                if fund and draft_move:
                    fund._refresh_draft_move(draft_move)
            rec.paid_date = False
            rec.state = 'approved'
            rec.message_post(body=_('Payment cancelled. Request reset to approved.'))

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Request'),
            'res_model': 'petty.cash.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.approved_by = False
            rec.approved_date = False
            rec.amount = 0.0
            transactions = self.env['petty.cash.transaction'].search([('request_id', '=', rec.id)])
            fund = rec.fund_id
            for txn in transactions:
                draft_move = txn.move_id if txn.move_id and txn.move_id.state == 'draft' else False
                txn.unlink()
                if fund and draft_move:
                    fund._refresh_draft_move(draft_move)

    def action_view_fund_journal_entries(self):
        self.ensure_one()
        return self.fund_id.action_view_journal_entries()
