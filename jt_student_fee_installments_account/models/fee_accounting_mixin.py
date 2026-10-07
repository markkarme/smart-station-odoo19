# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


PRODUCT_XMLIDS = {
    'basic': 'jt_student_fee_installments_account.product_fee_basic',
    'bus': 'jt_student_fee_installments_account.product_fee_bus',
    'books': 'jt_student_fee_installments_account.product_fee_books',
    'uniform': 'jt_student_fee_installments_account.product_fee_uniform',
}

CONFIG_KEYS = {
    'basic': 'jt_student_fee_installments_account.product_basic_id',
    'bus': 'jt_student_fee_installments_account.product_bus_id',
    'books': 'jt_student_fee_installments_account.product_books_id',
    'uniform': 'jt_student_fee_installments_account.product_uniform_id',
}


class StudentFeeAccountingMixin(models.AbstractModel):
    _name = 'student.fee.accounting.mixin'
    _description = 'Student Fee Accounting Mixin'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        copy=False,
        readonly=True,
        domain=[('move_type', '=', 'out_invoice')],
    )
    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='Invoice Status',
    )
    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='Invoice Payment Status',
    )

    def _fee_accounting_category(self):
        raise NotImplementedError

    def _fee_accounting_amount(self):
        raise NotImplementedError

    def _fee_accounting_description(self):
        self.ensure_one()
        return self.name or _('Student Fee')

    def _fee_accounting_partner(self):
        self.ensure_one()
        return self.student_id

    def _fee_accounting_date(self):
        self.ensure_one()
        return fields.Date.context_today(self)

    def _get_fee_product(self, category):
        ICP = self.env['ir.config_parameter'].sudo()
        product_id = ICP.get_param(CONFIG_KEYS.get(category, ''))
        product = self.env['product.product']
        if product_id and str(product_id).isdigit():
            product = product.browse(int(product_id)).exists()
        if not product:
            xmlid = PRODUCT_XMLIDS.get(category)
            if xmlid:
                product = self.env.ref(xmlid, raise_if_not_found=False)
        if not product:
            raise UserError(_(
                'No product configured for fee category "%s". '
                'Set it under Settings → Student Fee Accounting.',
                category,
            ))
        return product

    def _prepare_fee_invoice_vals(self):
        self.ensure_one()
        partner = self._fee_accounting_partner()
        if not partner:
            raise UserError(_('Student is required to create an invoice.'))
        amount = self._fee_accounting_amount()
        if amount <= 0:
            raise UserError(_('Invoice amount must be greater than zero.'))
        product = self._get_fee_product(self._fee_accounting_category())
        company = self.plan_id.company_id if self.plan_id else self.env.company
        return {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'company_id': company.id,
            'invoice_date': self._fee_accounting_date(),
            'currency_id': (self.currency_id or company.currency_id).id,
            'ref': self.receipt_number or False,
            'invoice_origin': self.plan_id.display_name if self.plan_id else False,
            'narration': self.note or False,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': self._fee_accounting_description(),
                'quantity': 1.0,
                'price_unit': amount,
            })],
        }

    def _invoice_link_vals(self):
        """Extra values written on account.move (reverse links)."""
        return {}

    def action_create_invoice(self):
        invoices = self.env['account.move']
        for line in self:
            if line.invoice_id and line.invoice_id.state != 'cancel':
                raise UserError(_(
                    'An invoice already exists for %(name)s (%(invoice)s).',
                    name=line.display_name or line.name,
                    invoice=line.invoice_id.display_name,
                ))
            vals = line._prepare_fee_invoice_vals()
            vals.update(line._invoice_link_vals())
            invoice = self.env['account.move'].create(vals)
            line.invoice_id = invoice.id
            invoices |= invoice

        # Single invoice: open payment wizard so user can mark it paid immediately
        if len(invoices) == 1 and self.env.context.get('open_payment_after_invoice', True):
            invoice = invoices
            if invoice.state == 'draft':
                invoice.action_post()
            return invoice.with_context(
                active_model='account.move',
                active_ids=invoice.ids,
                active_id=invoice.id,
            ).action_register_payment()

        if len(invoices) == 1:
            return {
                'name': _('Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoices.id,
                'target': 'current',
            }
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
            'target': 'current',
        }

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No invoice linked.'))
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }

    def action_register_payment(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('Create an invoice first.'))
        if self.invoice_id.state == 'draft':
            self.invoice_id.action_post()
        if self.invoice_id.state != 'posted':
            raise UserError(_('Post the invoice before registering a payment.'))
        return self.invoice_id.with_context(
            active_model='account.move',
            active_ids=self.invoice_id.ids,
            active_id=self.invoice_id.id,
        ).action_register_payment()

    def _apply_invoice_payment_sync(self, invoice):
        raise NotImplementedError
