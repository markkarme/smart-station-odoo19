# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class UpdateEffectiveDate(models.TransientModel):
    _name = 'update.effective.date'
    _description = 'Update Stock Picking Effective Date'

    date_done = fields.Datetime(
        string='Effective Date',
        required=True,
        default=fields.Datetime.now,
    )

    def update_date_done(self):
        self.ensure_one()
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        if not picking:
            raise UserError(_('No stock picking found to update.'))
        if picking.state not in ('done', 'cancel'):
            raise UserError(_(
                'You can only update the effective date on done or cancelled transfers.'
            ))
        if not self.date_done:
            raise UserError(_('Please set an effective date.'))
        picking.write({'date_done': self.date_done})
        return {'type': 'ir.actions.act_window_close'}
