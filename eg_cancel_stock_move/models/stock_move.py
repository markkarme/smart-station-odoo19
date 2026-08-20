# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _eg_create_reverse_done_move(self):
        """Create and validate a reverse move to undo a done stock move."""
        self.ensure_one()
        if float_is_zero(self.quantity, precision_rounding=self.product_uom.rounding):
            raise UserError(_(
                'Cannot reverse done move %(reference)s: quantity is zero.',
                reference=self.reference or self.display_name,
            ))
        reverse = self.env['stock.move'].create({
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'product_uom_qty': self.quantity,
            'location_id': self.location_dest_id.id,
            'location_dest_id': self.location_id.id,
            'company_id': self.company_id.id,
            'origin': _('Reversal of: %s', self.reference or self.display_name),
            'procure_method': 'make_to_stock',
        })
        reverse._action_confirm(merge=False)
        reverse._action_assign()
        if float_is_zero(reverse.quantity, precision_rounding=reverse.product_uom.rounding):
            reverse.quantity = self.quantity
        reverse.picked = True
        reverse._action_done()
        return reverse

    def bulk_stock_move_line_cancel(self):
        """Cancel selected stock moves (reverse done moves first)."""
        for move in self:
            if move.state == 'cancel':
                continue
            if move.state == 'done':
                move._eg_create_reverse_done_move()
                move.write({'state': 'cancel'})
            else:
                move._action_cancel()
        return True

    def bulk_stock_move_line_cancel_reset(self):
        """Cancel/reverse selected stock moves and reset them to draft."""
        for move in self:
            if move.state == 'draft':
                continue
            if move.state == 'done':
                move._eg_create_reverse_done_move()
            elif move.state != 'cancel':
                move._do_unreserve()
            move.write({'state': 'draft'})
        return True
