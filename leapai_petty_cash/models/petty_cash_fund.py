from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PettyCashFund(models.Model):
    _name = 'petty.cash.fund'
    _description = 'Petty Cash Fund'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Fund Name', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    account_id = fields.Many2one('account.account', string='Cash Account', tracking=True,
        help='Dedicated account for this petty cash fund')
    journal_id = fields.Many2one('account.journal', string='Cash Journal', tracking=True,
        help='Dedicated journal for petty cash transactions')
    journal_default_account_id = fields.Many2one(
        'account.account', related='journal_id.default_account_id')
    initial_balance = fields.Monetary(string='Initial Balance', currency_field='currency_id', tracking=True)
    current_balance = fields.Monetary(string='Current Balance', compute='_compute_current_balance',
        currency_field='currency_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True)
    request_ids = fields.One2many('petty.cash.request', 'fund_id', string='Requests')
    transaction_ids = fields.One2many('petty.cash.transaction', 'fund_id', string='Transactions')
    move_ids = fields.One2many(
        'account.move', 'petty_cash_fund_id', string='Journal Entries', copy=False)
    move_count = fields.Integer(compute='_compute_journal_counts', string='Journal Entries')
    unjournalized_transaction_count = fields.Integer(
        compute='_compute_journal_counts', string='Unjournalized Transactions')
    request_count = fields.Integer(compute='_compute_request_count', string='Requests')
    transaction_count = fields.Integer(compute='_compute_transaction_count', string='Transactions')
    notes = fields.Text(string='Notes')
    actual_spent_amount = fields.Monetary(string='Actual Spent Amount', currency_field='currency_id', compute='_compute_actual_spent_amount')
    current_journal_account_balance = fields.Monetary(string='Current Journal Account Balance', currency_field='currency_id', compute='_compute_current_journal_account_balance')
    expected_balance = fields.Monetary(string='Expected Balance', currency_field='currency_id', compute='_compute_expected_balance')
    @api.depends('initial_balance', 'current_balance')
    def _compute_actual_spent_amount(self):
        for fund in self:
            fund.actual_spent_amount = fund.initial_balance - fund.current_balance
    
    @api.depends('account_id', 'account_id.current_balance')
    def _compute_current_journal_account_balance(self):
        for fund in self:
            fund.current_journal_account_balance = fund.account_id.current_balance
    
    @api.depends('current_journal_account_balance', 'actual_spent_amount')
    def _compute_expected_balance(self):
        for fund in self:
            fund.expected_balance = fund.current_journal_account_balance - fund.actual_spent_amount

    @api.depends('transaction_ids', 'transaction_ids.debit', 'transaction_ids.credit', 'initial_balance')
    def _compute_current_balance(self):
        for fund in self:
            total_debit = sum(fund.transaction_ids.mapped('debit'))
            total_credit = sum(fund.transaction_ids.mapped('credit'))
            fund.current_balance = fund.initial_balance + total_debit - total_credit
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            self.account_id = self.journal_id.default_account_id
    def _compute_request_count(self):
        for fund in self:
            fund.request_count = self.env['petty.cash.request'].search_count([('fund_id', '=', fund.id)])

    def _compute_transaction_count(self):
        for fund in self:
            fund.transaction_count = len(fund.transaction_ids)

    @api.depends('move_ids', 'transaction_ids.move_id')
    def _compute_journal_counts(self):
        for fund in self:
            fund.move_count = len(fund.move_ids)
            fund.unjournalized_transaction_count = len(
                fund.transaction_ids.filtered(lambda t: not t.move_id))

    def _get_unjournalized_transactions(self):
        self.ensure_one()
        return self.transaction_ids.filtered(lambda t: not t.move_id)

    def _get_default_expense_account(self):
        self.ensure_one()
        return self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', self.company_id.id),
        ], limit=1)

    def _get_default_opening_account(self):
        self.ensure_one()
        return self.env['account.account'].search([
            ('account_type', 'in', ('equity', 'liability_current')),
            ('company_ids', 'in', self.company_id.id),
        ], limit=1)

    def _prepare_journal_entry_lines(self, transactions):
        self.ensure_one()
        expense_account = self._get_default_expense_account()
        opening_account = self._get_default_opening_account()
        if not expense_account:
            raise UserError(_('No expense account found. Please configure an expense account.'))
        if not opening_account:
            raise UserError(_('No opening account found. Please configure an equity or current liability account.'))
        if not self.account_id:
            raise UserError(_('Please set the cash account on this fund before creating a journal entry.'))
        if not transactions:
            raise UserError(_('There are no transactions to include in the journal entry.'))

        line_vals = []
        for txn in transactions.sorted('date,id'):
            if txn.credit:
                expense_line = {
                    'account_id': expense_account.id,
                    'name': txn.description,
                    'debit': txn.credit,
                    'credit': 0.0,
                }
                if txn.request_id and txn.request_id.analytic_distribution:
                    expense_line['analytic_distribution'] = txn.request_id.analytic_distribution
                line_vals.extend([
                    (0, 0, expense_line),
                    (0, 0, {
                        'account_id': self.account_id.id,
                        'name': txn.description,
                        'debit': 0.0,
                        'credit': txn.credit,
                    }),
                ])
            if txn.debit:
                line_vals.extend([
                    (0, 0, {
                        'account_id': self.account_id.id,
                        'name': txn.description,
                        'debit': txn.debit,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'account_id': opening_account.id,
                        'name': txn.description,
                        'debit': 0.0,
                        'credit': txn.debit,
                    }),
                ])
        return line_vals

    def _refresh_draft_move(self, move):
        """Rebuild a draft journal entry after its linked transactions change."""
        self.ensure_one()
        if not move or move.state != 'draft':
            return
        transactions = self.env['petty.cash.transaction'].search([('move_id', '=', move.id)])
        if not transactions:
            move.unlink()
            return
        line_vals = self._prepare_journal_entry_lines(transactions)
        move.line_ids.unlink()
        move.write({
            'date': max(transactions.mapped('date')),
            'line_ids': line_vals,
        })

    def action_create_journal_entry(self):
        for fund in self:
            if not fund.journal_id:
                raise UserError(_('Please set a journal on this petty cash fund first.'))
            transactions = fund._get_unjournalized_transactions()
            if not transactions:
                raise UserError(_('All transactions already have a journal entry.'))

            line_vals = fund._prepare_journal_entry_lines(transactions)
            move = self.env['account.move'].create({
                'journal_id': fund.journal_id.id,
                'date': max(transactions.mapped('date')),
                'ref': fund.name,
                'petty_cash_fund_id': fund.id,
                'line_ids': line_vals,
            })
            transactions.write({'move_id': move.id})
            fund.message_post(body=_(
                'Draft journal entry created for %d transaction(s).') % len(transactions))
        return True

    def action_view_journal_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('petty_cash_fund_id', '=', self.id)],
            'context': {'default_petty_cash_fund_id': self.id},
        }

    def action_setup_fund(self):
        """Create account and journal automatically for this fund."""
        self.ensure_one()
        if not self.account_id:
            # Create a dedicated cash account
            account_vals = {
                'name': f'Petty Cash - {self.employee_id.name}',
                'code': self._get_next_account_code(),
                'account_type': 'asset_cash',
                'company_ids': [(4, self.company_id.id)],
                'currency_id': self.currency_id.id,
            }
            account = self.env['account.account'].create(account_vals)
            self.account_id = account

        if not self.journal_id:
            # Create a dedicated journal
            journal_vals = {
                'name': f'Petty Cash - {self.employee_id.name}',
                'code': self._get_next_journal_code(),
                'type': 'cash',
                'default_account_id': self.account_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
            }
            journal = self.env['account.journal'].create(journal_vals)
            self.journal_id = journal

        # Create initial balance transaction if set
        if self.initial_balance and not self.transaction_ids:
            self.env['petty.cash.transaction'].create({
                'fund_id': self.id,
                'date': fields.Date.today(),
                'description': _('Initial Balance'),
                'debit': self.initial_balance,
                'credit': 0.0,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fund Setup Complete'),
                'message': _('Petty cash account and journal have been created successfully.'),
                'type': 'success',
            }
        }

    def _get_next_account_code(self):
        """Generate unique account code for petty cash."""
        existing = self.env['account.account'].search([('code', 'like', 'PC')], order='code desc', limit=1)
        if existing:
            try:
                num = int(existing.code.replace('PC', '')) + 1
            except Exception:
                num = 1
        else:
            num = 1
        return f'PC{num:03d}'

    def _get_next_journal_code(self):
        """Generate unique journal code for petty cash."""
        existing = self.env['account.journal'].search([('code', 'like', 'PC')], order='code desc', limit=1)
        if existing:
            try:
                num = int(existing.code.replace('PC', '')) + 1
            except Exception:
                num = 1
        else:
            num = 1
        return f'PC{num:02d}'

    def action_view_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Petty Cash Requests'),
            'res_model': 'petty.cash.request',
            'view_mode': 'list,form',
            'domain': [('fund_id', '=', self.id)],
            'context': {'default_fund_id': self.id, 'default_employee_id': self.employee_id.id},
        }

    def action_view_transactions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transactions'),
            'res_model': 'petty.cash.transaction',
            'view_mode': 'list,form',
            'domain': [('fund_id', '=', self.id)],
        }

    def action_set_inactive(self):
        self.state = 'inactive'

    def action_set_active(self):
        self.state = 'active'
