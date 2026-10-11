# -*- coding: utf-8 -*-
from odoo import fields, models


class BusCategory(models.Model):
    _name = 'bus.category'
    _description = 'فئة الباص'
    _order = 'name'

    name = fields.Char(string='اسم الباص', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    price = fields.Monetary(
        string='السعر',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )
    active = fields.Boolean(default=True)
