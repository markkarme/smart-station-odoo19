# -*- coding: utf-8 -*-
from odoo import fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def update_date_done(self):
        self.ensure_one()
        return {
            'name': _('Update Effective Date'),
            'type': 'ir.actions.act_window',
            'res_model': 'update.effective.date',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_date_done': self.date_done or fields.Datetime.now(),
                'active_id': self.id,
                'active_model': 'stock.picking',
            },
        }
