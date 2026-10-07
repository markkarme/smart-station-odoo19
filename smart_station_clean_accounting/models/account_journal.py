# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _smart_station_configure_paid_journals(self):
        """Use the journal liquidity account for customer receipts.

        A Bank journal normally parks receipts in Outstanding Receipts, so the
        invoice stays In Payment until the bank statement is reconciled.
        Setting the inbound payment account to the cash/bank account makes the
        invoice Paid as soon as the payment is registered.
        """
        companies = self.env['res.company'].sudo().search([])
        for company in companies:
            self._smart_station_ensure_cash_journal(company)
            journals = self.sudo().search([
                ('company_id', '=', company.id),
                ('type', 'in', ('bank', 'cash')),
            ])
            for journal in journals:
                self._smart_station_set_inbound_liquidity(journal)

    @api.model
    def _smart_station_ensure_cash_journal(self, company):
        Journal = self.sudo().with_company(company)
        if Journal.search_count([
            ('type', '=', 'cash'),
            ('company_id', '=', company.id),
        ]):
            return
        code = 'CSH1'
        index = 1
        while Journal.search_count([
            ('code', '=', code),
            ('company_id', '=', company.id),
        ]):
            index += 1
            code = 'CSH%s' % index
        journal = Journal.create({
            'name': 'Cash',
            'code': code,
            'type': 'cash',
            'company_id': company.id,
        })
        _logger.info(
            'Created cash journal %s (%s) for company %s',
            journal.display_name, journal.code, company.display_name,
        )

    @api.model
    def _smart_station_set_inbound_liquidity(self, journal):
        liquidity = journal.default_account_id
        if not liquidity or liquidity.account_type != 'asset_cash':
            liquidity = self.env['account.account'].sudo().search([
                ('account_type', '=', 'asset_cash'),
                ('company_ids', 'in', journal.company_id.id),
            ], limit=1)
        if not liquidity:
            _logger.warning(
                'No cash account for journal %s; inbound payments left unchanged.',
                journal.display_name,
            )
            return
        for line in journal.inbound_payment_method_line_ids:
            if line.payment_account_id == liquidity:
                continue
            line.sudo().write({'payment_account_id': liquidity.id})
            _logger.info(
                'Journal %s inbound method %s now uses %s',
                journal.display_name, line.display_name, liquidity.display_name,
            )
