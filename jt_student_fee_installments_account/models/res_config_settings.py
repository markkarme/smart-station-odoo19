# -*- coding: utf-8 -*-
from odoo import fields, models

from .fee_accounting_mixin import CONFIG_KEYS


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fee_product_basic_id = fields.Many2one(
        'product.product',
        string='Basic Fee Product',
        config_parameter=CONFIG_KEYS['basic'],
        domain=[('type', '=', 'service')],
    )
    fee_product_bus_id = fields.Many2one(
        'product.product',
        string='Bus Fee Product',
        config_parameter=CONFIG_KEYS['bus'],
        domain=[('type', '=', 'service')],
    )
    fee_product_books_id = fields.Many2one(
        'product.product',
        string='Books Fee Product',
        config_parameter=CONFIG_KEYS['books'],
        domain=[('type', '=', 'service')],
    )
    fee_product_uniform_id = fields.Many2one(
        'product.product',
        string='Uniform Fee Product',
        config_parameter=CONFIG_KEYS['uniform'],
        domain=[('type', '=', 'service')],
    )
